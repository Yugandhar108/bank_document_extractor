"""Export loan account summary to a formatted Excel workbook."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_Report.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
SECTION_FILL = PatternFill("solid", fgColor="D6E4F0")
THIN = Side(style="thin", color="B4B4B4")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, row: int, cols: int = 2) -> None:
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER


def style_section(ws, row: int, cols: int = 2) -> None:
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(bold=True, size=11)
        cell.fill = SECTION_FILL
        cell.border = BORDER


def write_table(ws, start_row: int, rows: list[tuple[str, str | float, str | None]]) -> int:
    row = start_row
    for label, value, note in rows:
        ws.cell(row=row, column=1, value=label).border = BORDER
        ws.cell(row=row, column=2, value=value).border = BORDER
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            ws.cell(row=row, column=2).number_format = '#,##0.00'
        if note:
            ws.cell(row=row, column=3, value=note).border = BORDER
            ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="top")
        row += 1
    return row


def autosize(ws, max_col: int = 3) -> None:
    for col in range(1, max_col + 1):
        letter = get_column_letter(col)
        max_len = 0
        for cell in ws[letter]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max(max_len + 2, 14), 55)


def build_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Loan Summary"

    ws["A1"] = "Union Bank of India - Loan Account Analysis Report"
    ws["A1"].font = Font(bold=True, size=14, color="1F4E79")
    ws.merge_cells("A1:C1")
    ws["A2"] = "Source: LoanAccountCompleteStatement.pdf | Generated from OCR + bank cumulative totals"
    ws.merge_cells("A2:C2")
    ws["A2"].font = Font(italic=True, size=10, color="666666")

    row = 4
    ws.cell(row=row, column=1, value="Field")
    ws.cell(row=row, column=2, value="Value")
    style_header(ws, row, 2)
    row += 1

    account_rows = [
        ("Account Holder", "PRASHANT INDURKAR / MS SMITA PRASHANT INDURKAR", None),
        ("Bank / Branch", "Union Bank of India, Civil Lines Nagpur", None),
        ("IFSC", "UBIN0544248", None),
        ("Loan Product", "Union Home - Floating Rate (TLU15)", None),
        ("Account Number", "442406650002092", None),
        ("Customer ID", "258299647", None),
        ("Statement Period", "01-Nov-2016 to 31-Jul-2026", None),
        ("Statement Generated", "01-Aug-2026", None),
    ]
    row = write_table(ws, row, account_rows)

    row += 1
    ws.cell(row=row, column=1, value="Principal Summary")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    style_section(ws, row, 2)
    row += 1
    row = write_table(
        ws,
        row,
        [
            ("Original loan sanctioned (INR)", 2500000.00, None),
            ("Additional disbursement - 21-Dec-2016 (INR)", 1400000.00, None),
            ("Total principal disbursed (INR)", 3900000.00, None),
            ("Estimated principal repaid (INR)", 3842730.72, None),
            ("Outstanding balance - 31-Jul-2026 (INR)", 57269.28, "Debit balance"),
            ("Principal repayment progress (%)", 98.53, None),
        ],
    )

    row += 1
    ws.cell(row=row, column=1, value="Interest Summary")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    style_section(ws, row, 2)
    row += 1
    row = write_table(
        ws,
        row,
        [
            ("Net interest paid - reconciled (INR)", 2419174.00, "Primary figure"),
            ("Interest reversal / COVID ex-gratia (INR)", 2918.68, "Credit in Nov-2020"),
            ("Normal interest - parsed OCR (INR)", 8023905.88, "OCR may over-count"),
            ("Penal interest - parsed OCR (INR)", 2660172.11, "OCR may over-count"),
            ("Interest as % of total paid", 38.2, "Percent"),
        ],
    )

    row += 1
    ws.cell(row=row, column=1, value="Repayment Summary")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    style_section(ws, row, 2)
    row += 1
    row = write_table(
        ws,
        row,
        [
            ("Total amount paid - bank cumulative (INR)", 6335829.68, "Authoritative"),
            ("Estimated EMI total @ Rs. 33,035 x 114 (INR)", 3765990.00, None),
            ("Regular EMI payments - parsed (INR)", 1524973.00, "Partial OCR parse"),
            ("Extra prepayments BBPS/NEFT/IMPS - parsed (INR)", 4964611.16, "Partial OCR parse"),
            ("Standard EMI amount (INR)", 33035.00, "Most months"),
            ("EMI occurrences detected", 114, "Count"),
        ],
    )

    row += 1
    ws.cell(row=row, column=1, value="Charges and Fees")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    style_section(ws, row, 2)
    row += 1
    row = write_table(
        ws,
        row,
        [
            ("Property insurance (INR)", 20631.00, "Feb-2017"),
            ("Legal vetting charges (INR)", 750.00, None),
            ("CERSAI charges (INR)", 1298.00, None),
            ("Total fees and charges - estimated (INR)", 73924.96, None),
        ],
    )

    row += 1
    ws.cell(row=row, column=1, value="Overall Bank Totals")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    style_section(ws, row, 2)
    row += 1
    row = write_table(
        ws,
        row,
        [
            ("Opening balance - 01-Nov-2016 (INR)", 2576751.00, "Dr"),
            ("Total withdrawals / debits (INR)", 6393098.96, "Cumulative"),
            ("Total deposits / credits (INR)", 6335829.68, "Cumulative"),
            ("Closing outstanding balance (INR)", 57269.28, "Dr"),
        ],
    )

    # Payment breakdown sheet
    bd = wb.create_sheet("Payment Breakdown")
    bd["A1"] = "Payment Breakdown (Reconciled)"
    bd["A1"].font = Font(bold=True, size=13, color="1F4E79")
    bd.merge_cells("A1:D1")
    headers = ["Component", "Amount (INR)", "Share (%)", "Notes"]
    for col, h in enumerate(headers, 1):
        bd.cell(row=3, column=col, value=h)
    style_header(bd, 3, 4)
    breakdown = [
        ("Total paid by borrower", 6335829.68, 100.0, "Bank cumulative deposits"),
        ("Principal component", 3842730.72, 60.7, "Disbursed minus outstanding"),
        ("Interest component", 2419174.00, 38.2, "Reconciled from totals"),
        ("Fees and charges", 73924.96, 1.2, "Insurance, legal, CERSAI, NESL"),
    ]
    r = 4
    for comp, amt, pct, notes in breakdown:
        bd.cell(row=r, column=1, value=comp).border = BORDER
        c = bd.cell(row=r, column=2, value=amt)
        c.number_format = '#,##0.00'
        c.border = BORDER
        bd.cell(row=r, column=3, value=pct).border = BORDER
        bd.cell(row=r, column=3).number_format = "0.0"
        bd.cell(row=r, column=4, value=notes).border = BORDER
        r += 1
    autosize(bd, 4)

    # Notes sheet
    notes_ws = wb.create_sheet("Notes")
    notes_ws["A1"] = "Other Details and Notes"
    notes_ws["A1"].font = Font(bold=True, size=13, color="1F4E79")
    note_lines = [
        "EMI payer changed from SMITA to YUGANDHAR PRASHANT INDURKAR around Jan-2020.",
        "Multiple part-prepayments via BBPS Credit Card Division from Dec-2022 onward.",
        "Large NEFT/IMPS prepayments observed in 2021-2025.",
        "Loan nearing full closure - only Rs. 57,269.28 outstanding as of 31-Jul-2026.",
        "Floating rate home loan; monthly interest accrual posted as Normal Int./NInt.",
        "Penal interest entries are minimal (late payment charges).",
        "PDF was scanned; reconciled figures use bank cumulative totals on the final statement page.",
        "Parsed OCR line totals may differ from reconciled figures due to OCR noise on balance columns.",
    ]
    for i, line in enumerate(note_lines, start=3):
        notes_ws.cell(row=i, column=1, value=line)
        notes_ws.cell(row=i, column=1).alignment = Alignment(wrap_text=True)
    notes_ws.column_dimensions["A"].width = 90

    autosize(ws, 2)
    ws.column_dimensions["C"].width = 28
    return wb


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb = build_workbook()
    wb.save(OUTPUT_PATH)
    print(f"Saved Excel report to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
