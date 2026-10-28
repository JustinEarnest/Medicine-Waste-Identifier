"""
Catalogue processing, normalization, and quality report generation
as defined in plan.md (Phase 1 & Phase 2).
"""
import os
import re
import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = BASE_DIR / "dataset" / "raw" / "indian_medicines_original.csv"
CLEANED_JSON = BASE_DIR / "dataset" / "cleaned_catalogue.json"
REPORTS_DIR = BASE_DIR / "dataset" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
QUALITY_REPORT = REPORTS_DIR / "catalogue_quality_report.md"

DOSAGE_FORMS = [
    "TABLET", "CAPSULE", "SYRUP", "INJECTION", "SUSPENSION", "DROPS",
    "OINTMENT", "GEL", "CREAM", "INHALER", "SOLUTION", "LOTION",
    "SPRAY", "EMULSION", "POWDER", "RESPULES", "INFUSION", "EYE DROPS", "EAR DROPS"
]

def extract_strength(name: str) -> str:
    """Extracts strength expressions like 500mg, 625 Duo, 400mg, 10ml, etc."""
    match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|%|iu))\b', name, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_dosage_form(name: str) -> str:
    """Extracts known pharmaceutical dosage form."""
    upper = name.upper()
    for df in DOSAGE_FORMS:
        if df in upper:
            return df.title()
    return "Other"

def normalize_text(text: str) -> str:
    """Strips non-alphanumeric chars and normalizes whitespace."""
    if not text:
        return ""
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    return ' '.join(text.split()).lower()

def main():
    if not RAW_CSV.exists():
        print(f"Error: Raw CSV not found at {RAW_CSV}")
        return

    print(f"Reading raw dataset: {RAW_CSV}")
    records = []
    total_rows = 0
    missing_manufacturers = 0
    missing_composition = 0
    missing_image_urls = 0
    unique_names = set()

    with open(RAW_CSV, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            raw_name = (row.get("Medicine Name") or "").strip()
            raw_composition = (row.get("Composition") or "").strip()
            raw_mfr = (row.get("Manufacturer") or "").strip()
            raw_uses = (row.get("Uses") or "").strip()
            raw_side_effects = (row.get("Side_effects") or "").strip()
            raw_img_url = (row.get("Image URL") or "").strip()

            if not raw_mfr:
                missing_manufacturers += 1
            if not raw_composition:
                missing_composition += 1
            if not raw_img_url:
                missing_image_urls += 1

            clean_name = normalize_text(raw_name)
            strength = extract_strength(raw_name)
            dosage_form = extract_dosage_form(raw_name)

            record = {
                "id": total_rows,
                "name": raw_name,
                "normalized_name": clean_name,
                "strength": strength,
                "dosage_form": dosage_form,
                "composition": raw_composition,
                "manufacturer": raw_mfr,
                "normalized_manufacturer": normalize_text(raw_mfr),
                "uses": raw_uses,
                "side_effects": raw_side_effects,
                "image_url": raw_img_url,
            }
            records.append(record)
            unique_names.add(clean_name)

    print(f"Total records processed: {total_rows}")
    print(f"Unique normalized medicine names: {len(unique_names)}")

    # Write cleaned catalogue JSON
    with open(CLEANED_JSON, mode="w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Cleaned catalogue saved to {CLEANED_JSON} ({CLEANED_JSON.stat().st_size} bytes)")

    # Write Quality Report
    report_md = f"""# Indian Medicine Catalogue - Data Quality Report

- **Source File:** `dataset/raw/indian_medicines_original.csv`
- **Cleaned Target:** `dataset/cleaned_catalogue.json`
- **Total Catalogue Records:** {total_rows:,}
- **Unique Normalized Brands/Formulations:** {len(unique_names):,}
- **Records with Missing Manufacturer:** {missing_manufacturers:,} ({missing_manufacturers/total_rows*100:.2f}%)
- **Records with Missing Active Composition:** {missing_composition:,} ({missing_composition/total_rows*100:.2f}%)
- **Records with Image URLs:** {total_rows - missing_image_urls:,} ({(total_rows - missing_image_urls)/total_rows*100:.2f}%)

## Attribute Normalization Summary
1. `name`: Preserved original trade name, formulation, and strength (e.g. *Augmentin 625 Duo Tablet*).
2. `normalized_name`: Lowercase alphanumeric tokens for high-speed indexing & token-set fuzzy matching.
3. `strength`: Extracted metric strength candidates (*500mg, 625 Duo, 400mg, 10ml*).
4. `dosage_form`: Classified into standard delivery categories (*Tablet, Capsule, Syrup, Injection, Suspension, etc.*).
5. `composition`: Extracted API active salt combinations.
6. `manufacturer`: Pharmaceutical corporate entity in India.

## Compliance & Usage
- Cleaned catalogue is deployed for front-side OCR candidate verification and matching.
- It operates strictly as a reference database to confirm product authenticity and prevent AI hallucination.
"""
    with open(QUALITY_REPORT, mode="w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Quality report saved to {QUALITY_REPORT}")

if __name__ == "__main__":
    main()
