"""OCR loan statement PDF using RapidOCR."""
from pathlib import Path

import pymupdf
from rapidocr_onnxruntime import RapidOCR

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "data" / "input" / "LoanAccountCompleteStatement.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_extracted.txt"
DPI = 300


def main() -> None:
    ocr = RapidOCR()
    zoom = DPI / 72
    matrix = pymupdf.Matrix(zoom, zoom)
    chunks: list[str] = []

    with pymupdf.open(str(PDF_PATH)) as document:
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix)
            image_path = PROJECT_ROOT / "data" / "output" / f"_ocr_page_{index + 1:02d}.png"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(str(image_path))
            result, _ = ocr(str(image_path))
            lines = [entry[1] for entry in (result or []) if entry and len(entry) > 1]
            page_text = "\n".join(lines)
            chunks.append(f"--- PAGE {index + 1} ---\n{page_text}")
            image_path.unlink(missing_ok=True)

    full_text = "\n\n".join(chunks)
    OUTPUT_PATH.write_text(full_text, encoding="utf-8")
    print(f"Saved {len(full_text)} characters to {OUTPUT_PATH}")
    print(full_text)


if __name__ == "__main__":
    main()
