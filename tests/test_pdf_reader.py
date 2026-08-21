"""Tests for safe PDF text extraction."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.ingestion.pdf_reader import (
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


def test_returns_empty_text_for_a_scanned_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"placeholder")

    class EmptyReader:
        pages = [FakePage(None)]

        def __init__(self, _: str) -> None:
            pass

    with patch("src.ingestion.pdf_reader.PdfReader", EmptyReader):
        result = read_pdf_text(pdf_path, tmp_path)

    assert result == ""


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
