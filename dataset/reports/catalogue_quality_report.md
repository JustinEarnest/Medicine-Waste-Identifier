# Indian Medicine Catalogue - Data Quality Report

- **Source File:** `dataset/raw/indian_medicines_original.csv`
- **Cleaned Target:** `dataset/cleaned_catalogue.json`
- **Total Catalogue Records:** 11,825
- **Unique Normalized Brands/Formulations:** 11,498
- **Records with Missing Manufacturer:** 0 (0.00%)
- **Records with Missing Active Composition:** 0 (0.00%)
- **Records with Image URLs:** 11,825 (100.00%)

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
