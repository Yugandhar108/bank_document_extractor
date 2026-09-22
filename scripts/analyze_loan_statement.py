"""Parse OCR loan statement text and compute financial summary."""
from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_extracted.txt"

INTEREST_HINT = re.compile(r"NORMALINT|NORMAL INT|NINT\.|NINT:|PENALINT|PENAL INT|PINT\.|PINT:", re.I)
EMI_HINT = re.compile(r"\bEMI\b|NACH/EMI|/EMI|ETXN/BY:.*EMI", re.I)
PREPAY_HINT = re.compile(r"LOAN REPAYMENT|LOAN RECOVERY|NEFT:|IMPSAB/", re.I)
AMOUNT_TOKEN = re.compile(
    r"(\d{1,2}[.,]\d{2,3}(?:[.,]\d{2,3})*(?:\.\d{1,2})?|\d{3,7}(?:\.\d{1,2})?)"
)


def normalize_amount(token: str) -> Decimal | None:
    token = token.strip().replace("Dr", "").replace("Cr", "")
    if token.count(".") > 1:
        parts = token.split(".")
        if len(parts[-1]) == 2:
            token = "".join(parts[:-1]) + "." + parts[-1]
    token = token.replace(",", "")
    try:
        return Decimal(token)
    except InvalidOperation:
        return None


def amount_from_line(line: str) -> Decimal | None:
    if re.search(r"\dDr$", line.replace(" ", "")):
        return None
    match = AMOUNT_TOKEN.search(line)
    if not match:
        return None
    value = normalize_amount(match.group(1))
    if value is None or value > Decimal("500000"):
        return None
    return value


def fmt(value: Decimal | float | int) -> str:
    number = float(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    whole = int(number)
    frac = int(round((number - whole) * 100))
    text = str(whole)
    if len(text) > 3:
        last3 = text[-3:]
        rest = text[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        text = ",".join(groups + [last3])
    return f"{sign}Rs. {text}.{frac:02d}"


def parse_categories(text: str) -> tuple[dict[str, Decimal], Counter]:
    totals = {
        "normal_interest": Decimal("0"),
        "penal_interest": Decimal("0"),
        "emi_payments": Decimal("0"),
        "extra_repayments": Decimal("0"),
        "insurance": Decimal("0"),
        "fees": Decimal("0"),
        "interest_reversal": Decimal("0"),
    }
    counts: Counter = Counter()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    recent = ""

    for idx, line in enumerate(lines):
        if line.startswith("--- PAGE") or line.startswith("http") or "Cumulative" in line:
            continue
        recent = f"{recent} {line}"[-300:]

        amount = amount_from_line(line)
        if amount is None and idx + 1 < len(lines):
            amount = amount_from_line(lines[idx + 1])

        if amount is None:
            continue

        upper_recent = recent.upper()
        if INTEREST_HINT.search(upper_recent):
            if re.search(r"PENAL|PINT", upper_recent):
                totals["penal_interest"] += amount
                counts["penal_interest"] += 1
            else:
                totals["normal_interest"] += amount
                counts["normal_interest"] += 1
        elif EMI_HINT.search(upper_recent):
            totals["emi_payments"] += amount
            counts["emi_payments"] += 1
        elif PREPAY_HINT.search(upper_recent):
            totals["extra_repayments"] += amount
            counts["extra_repayments"] += 1
        elif "PROPERTY INSURANCE" in upper_recent:
            totals["insurance"] += amount
            counts["insurance"] += 1
        elif any(k in upper_recent for k in ("VETTING", "CERSAI", "NESL")):
            totals["fees"] += amount
            counts["fees"] += 1
        elif "GO1 EX GRATIA" in upper_recent or "COMPOUND INTEREST REVERSAL" in upper_recent:
            totals["interest_reversal"] += amount
            counts["interest_reversal"] += 1

    return totals, counts


def main() -> None:
    text = TEXT_PATH.read_text(encoding="utf-8")
    totals, counts = parse_categories(text)

    cumulative_deposits = Decimal("6335829.68")
    cumulative_withdrawals = Decimal("6393098.96")
    closing_balance = Decimal("57269.28")
    opening_balance = Decimal("2576751")
    total_disbursed = Decimal("3900000")

    total_interest_parsed = totals["normal_interest"] + totals["penal_interest"]
    net_interest_parsed = total_interest_parsed - totals["interest_reversal"]
    total_fees = totals["insurance"] + totals["fees"]

    # Authoritative reconciliation using bank cumulative deposits
    principal_repaid = total_disbursed - closing_balance
    net_interest = cumulative_deposits - principal_repaid - total_fees
    total_charges = total_fees

    emi_standard_count = len(re.findall(r"33[,.\s]?035(?:\.00)?", text))

    lines = [
        "LOAN ACCOUNT DETAILED SUMMARY",
        "================================",
        "",
        "Account Holder: PRASHANT INDURKAR / MS SMITA PRASHANT INDURKAR",
        "Bank: Union Bank of India, Civil Lines Nagpur",
        "Branch IFSC: UBIN0544248",
        "Loan Product: Union Home - Floating Rate (TLU15)",
        "Account Number: 442406650002092",
        "Customer ID: 258299647",
        "Statement Period: 01-Nov-2016 to 31-Jul-2026",
        "Statement Generated: 01-Aug-2026",
        "",
        "--- PRINCIPAL ---",
        f"Original loan sanctioned: Rs. 25,00,000.00",
        f"Additional disbursement (21-Dec-2016): Rs. 14,00,000.00",
        f"Total principal disbursed: {fmt(total_disbursed)}",
        f"Outstanding balance (31-Jul-2026): {fmt(closing_balance)} Dr",
        f"Estimated principal repaid: {fmt(principal_repaid)}",
        f"Principal repayment progress: {float(principal_repaid / total_disbursed * 100):.2f}%",
        "",
        "--- INTEREST ---",
        f"Normal interest (parsed, {counts['normal_interest']} entries): {fmt(totals['normal_interest'])}",
        f"Penal interest (parsed, {counts['penal_interest']} entries): {fmt(totals['penal_interest'])}",
        f"Interest reversal / COVID ex-gratia credit: {fmt(totals['interest_reversal'])}",
        f"Net interest paid (reconciled from bank totals): {fmt(net_interest)}",
        "",
        "--- REPAYMENTS ---",
        f"Regular EMI payments (parsed, {counts['emi_payments']} entries): {fmt(totals['emi_payments'])}",
        f"Standard Rs. 33,035 EMI occurrences detected: {emi_standard_count}",
        f"Estimated EMI total (@ Rs. 33,035): {fmt(Decimal(emi_standard_count) * Decimal('33035'))}",
        f"Extra prepayments - BBPS / NEFT / IMPS ({counts['extra_repayments']} entries): {fmt(totals['extra_repayments'])}",
        f"TOTAL AMOUNT PAID (bank cumulative deposits): {fmt(cumulative_deposits)}",
        "",
        "--- CHARGES & FEES ---",
        f"Property insurance: {fmt(totals['insurance'])}",
        f"Processing / legal / CERSAI / NESL fees: {fmt(totals['fees'])}",
        f"Total fees & charges: {fmt(total_charges)}",
        "",
        "--- OVERALL BANK TOTALS ---",
        f"Opening balance (01-Nov-2016): {fmt(opening_balance)} Dr",
        f"Total withdrawals / debits: {fmt(cumulative_withdrawals)}",
        f"Total deposits / credits: {fmt(cumulative_deposits)}",
        f"Closing outstanding balance: {fmt(closing_balance)} Dr",
        "",
        "--- PAYMENT BREAKDOWN (RECONCILED) ---",
        f"Total paid by borrower: {fmt(cumulative_deposits)}",
        f"  - Principal component: {fmt(principal_repaid)} ({float(principal_repaid/cumulative_deposits*100):.1f}%)",
        f"  - Interest component: {fmt(net_interest)} ({float(net_interest/cumulative_deposits*100):.1f}%)",
        f"  - Fees & charges: {fmt(total_charges)} ({float(total_charges/cumulative_deposits*100):.1f}%)",
        "",
        "--- OTHER DETAILS ---",
        "EMI payer changed from SMITA to YUGANDHAR PRASHANT INDURKAR around Jan-2020.",
        "Multiple part-prepayments via BBPS Credit Card Division from Dec-2022 onward.",
        "Large NEFT/IMPS prepayments observed in 2021-2025.",
        "Loan nearing full closure - only Rs. 57,269.28 outstanding as of 31-Jul-2026.",
        "Floating rate home loan; monthly interest accrual posted as Normal Int./NInt.",
        "Penal interest entries are minimal (late payment charges).",
    ]

    output = "\n".join(lines)
    output_path = PROJECT_ROOT / "data" / "output" / "LoanAccountCompleteStatement_summary.txt"
    output_path.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
