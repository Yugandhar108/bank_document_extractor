"""Render loan statement PDF pages to PNG for visual analysis."""
from pathlib import Path

import pymupdf

PDF_PATH = Path(__file__).resolve().parents[1] / "data" / "input" / "LoanAccountCompleteStatement.pdf"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "output" / "loan_pages"
DPI = 200


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zoom = DPI / 72
    matrix = pymupdf.Matrix(zoom, zoom)
    with pymupdf.open(str(PDF_PATH)) as document:
        print(f"Pages: {document.page_count}")
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix)
            output_path = OUTPUT_DIR / f"page_{index + 1:02d}.png"
            pixmap.save(str(output_path))
            print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
