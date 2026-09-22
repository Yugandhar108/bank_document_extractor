"""Safe text extraction from PDF documents, with OCR fallback for scanned pages."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 25 * 1024 * 1024
DEFAULT_OCR_DPI = 300


class PdfReaderError(Exception):
    """Base error for PDF reading failures."""


class PdfPathError(PdfReaderError):
    """Raised when a PDF path is invalid or outside the allowed directory."""


class PdfTextError(PdfReaderError):
    """Raised when a PDF cannot be read or contains no text layer."""


class PdfOcrError(PdfReaderError):
    """Raised when OCR fallback fails for a scanned PDF."""


def _safe_pdf_path(pdf_path: str | Path, allowed_directory: str | Path) -> Path:
    """Resolve a PDF path and confirm it remains inside the allowed directory."""
    allowed_root = Path(allowed_directory).expanduser().resolve()
    candidate = Path(pdf_path).expanduser()
    resolved_path = candidate.resolve()

    try:
        resolved_path.relative_to(allowed_root)
    except ValueError as error:
        raise PdfPathError(
            f"PDF path must be inside the allowed directory: {allowed_root}"
        ) from error

    if resolved_path.suffix.lower() != ".pdf":
        raise PdfPathError("The selected file must have a .pdf extension.")
    if not resolved_path.is_file():
        raise PdfPathError(f"PDF file does not exist: {resolved_path}")
    if resolved_path.stat().st_size > MAX_PDF_BYTES:
        raise PdfPathError("PDF file is larger than the 25 MB safety limit.")

    return resolved_path


def _ocr_pdf_text(resolved_path: Path, dpi: int, tesseract_cmd: str | None) -> str:
    """Render each page to an image and run OCR to recover text from scanned pages."""
    try:
        import fitz  # PyMuPDF; imported lazily so OCR support stays optional
        import pytesseract
        from PIL import Image
    except ImportError as error:
        raise PdfOcrError(
            "OCR support requires the pymupdf, pytesseract, and pillow packages."
        ) from error

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    try:
        with fitz.open(str(resolved_path)) as document:
            page_text = []
            for page in document:
                pixmap = page.get_pixmap(matrix=matrix)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_text.append(pytesseract.image_to_string(image).strip())
    except pytesseract.TesseractNotFoundError as error:
        raise PdfOcrError(
            "OCR requires the Tesseract engine to be installed and available on PATH."
        ) from error
    except (OSError, RuntimeError, ValueError) as error:
        raise PdfOcrError(f"Could not run OCR on PDF: {resolved_path.name}") from error

    return "\n\n".join(text for text in page_text if text)


def read_pdf_text(
    pdf_path: str | Path,
    allowed_directory: str | Path,
    enable_ocr: bool = True,
    ocr_dpi: int = DEFAULT_OCR_DPI,
    tesseract_cmd: str | None = None,
) -> str:
    """Return text from every page of a PDF inside the allowed directory.

    When the PDF has no embedded text layer, as commonly happens with
    scanned-image PDFs, each page is rendered to an image and OCR is run to
    recover the text, unless ``enable_ocr`` is False.
    """
    resolved_path = _safe_pdf_path(pdf_path, allowed_directory)

    try:
        reader = PdfReader(str(resolved_path))
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as error:
        raise PdfTextError(f"Could not read PDF: {resolved_path.name}") from error

    text = "\n\n".join(entry for entry in page_text if entry)
    if text or not enable_ocr:
        return text

    return _ocr_pdf_text(resolved_path, dpi=ocr_dpi, tesseract_cmd=tesseract_cmd)
