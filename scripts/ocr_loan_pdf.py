"""OCR loan statement PDF using Windows OCR or Tesseract."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "data" / "input" / "LoanAccountCompleteStatement.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_extracted.txt"
DPI = 300


async def ocr_with_windows(image_path: Path) -> str:
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile
    from winrt.windows.storage.streams import DataReader

    file = await StorageFile.get_file_from_path_async(str(image_path))
    stream = await file.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR engine unavailable")
    result = await engine.recognize_async(bitmap)
    return result.text or ""


def render_pages() -> list[Path]:
    output_dir = PROJECT_ROOT / "data" / "output" / "loan_pages_hires"
    output_dir.mkdir(parents=True, exist_ok=True)
    zoom = DPI / 72
    matrix = pymupdf.Matrix(zoom, zoom)
    paths: list[Path] = []
    with pymupdf.open(str(PDF_PATH)) as document:
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix)
            output_path = output_dir / f"page_{index + 1:02d}.png"
            pixmap.save(str(output_path))
            paths.append(output_path)
    return paths


def ocr_with_tesseract(image_path: Path, tesseract_cmd: str) -> str:
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    return pytesseract.image_to_string(Image.open(image_path))


async def main() -> int:
    page_paths = render_pages()
    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    use_tesseract = Path(tesseract_cmd).is_file()
    chunks: list[str] = []

    for page_path in page_paths:
        if use_tesseract:
            text = ocr_with_tesseract(page_path, tesseract_cmd)
        else:
            text = await ocr_with_windows(page_path)
        chunks.append(f"--- PAGE {page_path.stem} ---\n{text.strip()}")

    full_text = "\n\n".join(chunks)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(full_text, encoding="utf-8")
    print(f"OCR method: {'tesseract' if use_tesseract else 'windows'}")
    print(f"Saved {len(full_text)} characters to {OUTPUT_PATH}")
    print(full_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
