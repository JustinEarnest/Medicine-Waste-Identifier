# Indian Medicines Dataset - Source & License Documentation

## Source Information
- **Dataset Title:** Indian Medicines Dataset (v1)
- **Hugging Face Repository:** [zenitsu09/medicine-dataset-v1](https://huggingface.co/datasets/zenitsu09/medicine-dataset-v1)
- **Primary Data File:** `Medicine_Details.csv`
- **Acquisition Date:** 2026-10-28
- **Reported License:** Apache-2.0
- **Total Records:** 11,825 rows

## Schema Definition
The dataset contains the following 9 attributes:
1. `Medicine Name`: Brand name, strength, and formulation (e.g., *Augmentin 625 Duo Tablet*).
2. `Composition`: Active pharmaceutical ingredients (API) and concentrations (e.g., *Amoxycillin (500mg) + Clavulanic Acid (125mg)*).
3. `Uses`: Clinical indications and medical conditions treated.
4. `Side_effects`: Common and documented adverse reactions.
5. `Image URL`: Direct link to product pack photography (hosted on Onemg CDN).
6. `Manufacturer`: Pharmaceutical manufacturing company in India.
7. `Excellent Review %`: Consumer satisfaction score (positive).
8. `Average Review %`: Consumer satisfaction score (neutral).
9. `Poor Review %`: Consumer satisfaction score (negative).

## Usage Limitations & Compliance
- Product photographs linked via third-party CDN are inspected selectively and not redistributed without verifying upstream hosting terms.
- Medicine indications and side effects are retained for informational catalogue matching and must **never** be used for clinical diagnosis or prescription recommendations.
- Names and compositions are normalized into lookup structures for OCR matching.
