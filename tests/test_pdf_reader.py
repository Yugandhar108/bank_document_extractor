"""Tests for safe PDF text extraction."""

from pathlib import Path
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.pdf_reader import (
    PdfOcrError,
    PdfPathError,
    PdfTextError,
    read_pdf_text,
)


class FakePage:
    def __init__(self, text: str | None) -> None:
        self.text = text

    def extract_text(self) -> str | None:
        return self.text


class FakeReader:
    def __init__(self, _: str) -> None:
        self.pages = [FakePage("Page one"), FakePage("Page two")]


def test_reads_and_joins_text_from_all_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.write_bytes(b"placeholder")

    with patch("src.ingestion.pdf_reader.PdfReader", FakeReader):
        result = read_pdf_text(pdf_path, tmp_path)

    assert result == "Page one\n\nPage two"


def test_rejects_a_path_outside_allowed_directory(tmp_path: Path) -> None:
    allowed_directory = tmp_path / "input"
    outside_pdf = tmp_path / "outside.pdf"
    allowed_directory.mkdir()
    outside_pdf.write_bytes(b"placeholder")

    with pytest.raises(PdfPathError, match="inside the allowed directory"):
        read_pdf_text(outside_pdf, allowed_directory)


def test_returns_empty_text_for_a_scanned_pdf_when_ocr_is_disabled(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"placeholder")

    class EmptyReader:
        pages = [FakePage(None)]

        def __init__(self, _: str) -> None:
            pass

    with patch("src.ingestion.pdf_reader.PdfReader", EmptyReader):
        result = read_pdf_text(pdf_path, tmp_path, enable_ocr=False)

    assert result == ""


def _install_fake_ocr_stack(monkeypatch, ocr_text: str = "OCR text", tesseract_error: type[Exception] | None = None) -> None:
    """Inject fake fitz/pytesseract/Pillow modules so OCR runs without native dependencies."""

    class FakeTesseractNotFoundError(Exception):
        pass

    fake_page = MagicMock()
    fake_page.get_pixmap.return_value = MagicMock(width=1, height=1, samples=b"\x00\x00\x00")

    fake_document = MagicMock()
    fake_document.__enter__ = MagicMock(return_value=[fake_page])
    fake_document.__exit__ = MagicMock(return_value=False)

    fake_fitz = types.ModuleType("fitz")
    fake_fitz.open = MagicMock(return_value=fake_document)
    fake_fitz.Matrix = MagicMock(return_value="matrix")

    fake_pytesseract = types.ModuleType("pytesseract")
    fake_pytesseract.pytesseract = MagicMock()
    fake_pytesseract.TesseractNotFoundError = tesseract_error or FakeTesseractNotFoundError
    if tesseract_error is not None:
        fake_pytesseract.image_to_string = MagicMock(side_effect=tesseract_error("Tesseract not found"))
    else:
        fake_pytesseract.image_to_string = MagicMock(return_value=ocr_text)

    fake_pil_image = types.ModuleType("PIL.Image")
    fake_pil_image.frombytes = MagicMock(return_value="fake-image")
    fake_pil = types.ModuleType("PIL")
    fake_pil.Image = fake_pil_image

    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setitem(sys.modules, "pytesseract", fake_pytesseract)
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_pil_image)


def test_uses_ocr_fallback_for_a_scanned_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"placeholder")

    class EmptyReader:
        pages = [FakePage(None)]

        def __init__(self, _: str) -> None:
            pass

    _install_fake_ocr_stack(monkeypatch, ocr_text="Recovered text")

    with patch("src.ingestion.pdf_reader.PdfReader", EmptyReader):
        result = read_pdf_text(pdf_path, tmp_path)

    assert result == "Recovered text"


def test_raises_a_clear_error_when_ocr_packages_are_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"placeholder")

    class EmptyReader:
        pages = [FakePage(None)]

        def __init__(self, _: str) -> None:
            pass

    monkeypatch.setitem(sys.modules, "fitz", None)

    with patch("src.ingestion.pdf_reader.PdfReader", EmptyReader):
        with pytest.raises(PdfOcrError, match="requires the pymupdf"):
            read_pdf_text(pdf_path, tmp_path)


def test_raises_a_clear_error_when_tesseract_is_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"placeholder")

    class EmptyReader:
        pages = [FakePage(None)]

        def __init__(self, _: str) -> None:
            pass

    class FakeTesseractNotFoundError(Exception):
        pass

    _install_fake_ocr_stack(monkeypatch, tesseract_error=FakeTesseractNotFoundError)

    with patch("src.ingestion.pdf_reader.PdfReader", EmptyReader):
        with pytest.raises(PdfOcrError, match="Tesseract engine"):
            read_pdf_text(pdf_path, tmp_path)


def test_reports_a_corrupted_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"not a PDF")

    with pytest.raises(PdfTextError, match="Could not read PDF"):
        read_pdf_text(pdf_path, tmp_path)


def test_rejects_a_pdf_over_the_resource_limit(tmp_path: Path) -> None:
    pdf_path = tmp_path / "large.pdf"
    with pdf_path.open("wb") as file:
        file.seek(25 * 1024 * 1024)
        file.write(b"x")

    with pytest.raises(PdfPathError, match="25 MB safety limit"):
        read_pdf_text(pdf_path, tmp_path)
