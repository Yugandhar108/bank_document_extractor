"""Safe text extraction from PDF documents."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 25 * 1024 * 1024


class PdfReaderError(Exception):
    """Base error for PDF reading failures."""


class PdfPathError(PdfReaderError):
    """Raised when a PDF path is invalid or outside the allowed directory."""


class PdfTextError(PdfReaderError):
    """Raised when a PDF cannot be read or contains no text layer."""


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


def read_pdf_text(
    pdf_path: str | Path,
    allowed_directory: str | Path,
) -> str:
    """Return text from every page of a PDF inside the allowed directory.

    An empty string means the PDF was readable but had no embedded text layer,
    which commonly happens with scanned-image PDFs.
    """
    resolved_path = _safe_pdf_path(pdf_path, allowed_directory)

    try:
        reader = PdfReader(str(resolved_path))
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as error:
        raise PdfTextError(f"Could not read PDF: {resolved_path.name}") from error

    return "\n\n".join(text for text in page_text if text)
