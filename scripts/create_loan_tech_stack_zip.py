"""Package loan analysis tech stack into a downloadable zip."""
from __future__ import annotations

import argparse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def add_file(zf: zipfile.ZipFile, path: Path, arc_prefix: str) -> None:
    if path.is_file():
        zf.write(path, arcname=f"{arc_prefix}/{path.name}")
        print(f"  + {arc_prefix}/{path.name}")
    elif path.is_dir():
        for file in sorted(path.rglob("*")):
            if file.is_file():
                rel = file.relative_to(path)
                zf.write(file, arcname=f"{arc_prefix}/{rel.as_posix()}")
                print(f"  + {arc_prefix}/{rel.as_posix()}")


def build_zip(zip_path: Path, include_page_images: bool) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    script_names = [
        "render_loan_pdf.py",
        "extract_loan_pdf.py",
        "ocr_loan_pdf.py",
        "rapidocr_loan_pdf.py",
        "analyze_loan_statement.py",
        "export_loan_summary_excel.py",
        "create_loan_tech_stack_zip.py",
    ]
    output_names = [
        "LoanAccountCompleteStatement_extracted.txt",
        "LoanAccountCompleteStatement_summary.txt",
        "LoanAccountCompleteStatement_Report.xlsx",
        "README_LOAN_TECH_STACK.md",
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Creating {zip_path} ...")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "MANIFEST.txt",
            "\n".join(
                [
                    "Loan Statement Analysis Tech Stack",
                    f"Packaged (UTC): {stamp}",
                    f"Includes page PNGs: {include_page_images}",
                    "",
                    "Contents:",
                    "  scripts/     Python pipeline",
                    "  outputs/     OCR text, summary, Excel",
                    "  loan_pages/  Rendered PNG pages (optional)",
                    "",
                    "See outputs/README_LOAN_TECH_STACK.md for usage.",
                ]
            ),
        )
        print("  + MANIFEST.txt")

        for name in script_names:
            path = SCRIPTS_DIR / name
            if path.is_file():
                add_file(zf, path, "scripts")

        for name in output_names:
            path = OUTPUT_DIR / name
            if path.is_file():
                add_file(zf, path, "outputs")

        if include_page_images:
            pages = OUTPUT_DIR / "loan_pages"
            if pages.is_dir():
                add_file(zf, pages, "loan_pages")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nDone: {zip_path}")
    print(f"Size: {size_mb:.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Zip loan analysis tech stack")
    parser.add_argument(
        "--lite",
        action="store_true",
        help="Omit loan_pages PNGs (smaller download)",
    )
    args = parser.parse_args()

    if args.lite:
        build_zip(OUTPUT_DIR / "LoanStatement_TechStack_Lite.zip", include_page_images=False)
    else:
        build_zip(OUTPUT_DIR / "LoanStatement_TechStack.zip", include_page_images=True)


if __name__ == "__main__":
    main()
