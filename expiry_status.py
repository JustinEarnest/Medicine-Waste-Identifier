"""
Phase B: Expiry Status Detection for Medicine Waste Identifier.

This module:
- Parses common expiry-date candidates such as MM/YYYY, MM/YY, and DD/MM/YYYY.
- Classifies a medicine as EXPIRED, NOT EXPIRED, or EXPIRY UNKNOWN.
- Uses the last day of the stated expiry month for MM/YYYY labels.
- Treats OCR-derived dates as candidates requiring human verification.

This is a standalone utility and can later be integrated into Django/FastAPI.
"""

from datetime import date, datetime
import re
from typing import Optional, Dict, Any


def parse_expiry_date(value: str) -> Optional[date]:
    """
    Parse an expiry date candidate into a date.

    Supported examples:
      10/2026        -> 31 October 2026 (end of month)
      10/26          -> 31 October 2026
      31/10/2026     -> 31 October 2026
      2026-10-31     -> 31 October 2026

    Returns None when the value is missing, ambiguous, or unsupported.
    The input may contain a trailing OCR marker such as '[VERIFY]'.
    """
    if not value:
        return None

    text = value.upper().strip()
    text = re.sub(r"\s*\[(?:VERIFY(?: OCR)?(?:\s*-\s*AMBIGUOUS)?)\]\s*$", "", text)
    text = text.replace(".", "/").replace("-", "/")
    text = re.sub(r"\s+", "", text)

    # Month/year: MM/YYYY or MM/YY
    match = re.fullmatch(r"(0?[1-9]|1[0-2])/(\d{2}|\d{4})", text)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        if year < 100:
            year += 2000
        if not 2000 <= year <= 2099:
            return None
        # Expiry month is treated as valid through its final calendar day.
        if month == 12:
            return date(year, 12, 31)
        return date(year, month + 1, 1).fromordinal(
            date(year, month + 1, 1).toordinal() - 1
        )

    # Day/month/year: DD/MM/YYYY
    match = re.fullmatch(r"(0?[1-9]|[12]\d|3[01])/(0?[1-9]|1[0-2])/(20\d{2})", text)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # ISO year/month/day
    match = re.fullmatch(r"(20\d{2})/(0?[1-9]|1[0-2])/([0-2]?\d|3[01])", text)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None


def classify_expiry(expiry_candidate: Optional[str], today: Optional[date] = None) -> Dict[str, Any]:
    """
    Return status and parsed date. OCR candidates must be verified by a person.
    If no parseable date is available, return EXPIRY UNKNOWN.
    """
    if today is None:
        today = date.today()

    parsed = parse_expiry_date(expiry_candidate or "")
    if parsed is None:
        return {
            "status": "EXPIRY UNKNOWN",
            "expiry_date": None,
            "message": "Expiry date could not be confidently parsed. Check the package manually.",
            "requires_verification": True,
        }

    if parsed < today:
        status = "EXPIRED"
        message = "The expiry date has passed. Do not use; follow local pharmacy/medical guidance for disposal."
    else:
        status = "NOT EXPIRED"
        message = "The parsed expiry date has not passed, but verify the printed label and package condition."
    return {
        "status": status,
        "expiry_date": parsed.isoformat(),
        "message": message,
        "requires_verification": True,
    }


def main() -> None:
    print("Medicine Waste Identifier — Phase B Expiry Status Test")
    print("Enter a detected expiry candidate (examples: 10/2026, 31/10/2026).")
    print("Press Enter without text to test EXPIRY UNKNOWN.")
    candidate = input("Expiry candidate: ").strip()
    result = classify_expiry(candidate)

    print("\nResult")
    print(f"Status: {result['status']}")
    print(f"Parsed expiry date: {result['expiry_date'] or 'NOT PARSED'}")
    print(f"Message: {result['message']}")
    print(f"Manual verification required: {'YES' if result['requires_verification'] else 'NO'}")


if __name__ == "__main__":
    main()
