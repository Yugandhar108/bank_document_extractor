"""One-off script to extract text from a loan statement PDF for analysis."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.pdf_reader import read_pdf_text

PDF_PATH = PROJECT_ROOT / "data" / "input" / "LoanAccountCompleteStatement.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_extracted.txt"


def main() -> None:
    allowed = PROJECT_ROOT / "data" / "input"
    text = read_pdf_text(PDF_PATH, allowed_directory=allowed, enable_ocr=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text)} characters from {PDF_PATH.name}")
    print(f"Saved to {OUTPUT_PATH}")
    print("--- BEGIN TEXT ---")
    print(text)
    print("--- END TEXT ---")


if __name__ == "__main__":
    main()
