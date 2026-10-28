"""
Back-side medicine expiry detection wrapper service.
Preserves existing YOLOv8 + EasyOCR model and weights without alteration (plan.md Phase 4).
"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import date

from .pipeline import process_medicine_image


def analyze_back_expiry(image_path: Path, output_dir: Path, file_stem: str = "back") -> Dict[str, Any]:
    """
    Executes the existing YOLOv8 + EasyOCR expiry date extraction pipeline on back packaging image.
    Standardizes output format and preserves raw vs normalized dates.
    """
    result = process_medicine_image(
        image_input=image_path,
        output_dir=output_dir,
        file_stem=file_stem
    )

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Back image expiry detection failed"),
            "mfg_date_raw": None,
            "mfg_date_normalized": None,
            "exp_date_raw": None,
            "exp_date_normalized": None,
            "parsed_expiry_date": None,
            "expiry_status": "REVIEW",
            "warnings": [result.get("error", "Processing error")]
        }

    warnings = []
    exp_date = result.get("exp_date", "")
    parsed_date = result.get("parsed_expiry_date")
    status = result.get("status", "REVIEW")

    if not exp_date:
        warnings.append("No explicit EXP/EXPIRY date found in the detected region.")
    if status == "REVIEW":
        warnings.append("Expiry status could not be verified automatically; please inspect physical packaging.")

    return {
        "success": True,
        "annotated_filename": result.get("annotated_filename"),
        "crop_filename": result.get("crop_filename"),
        "raw_ocr_text": result.get("raw_ocr_text", ""),
        "mfg_date_raw": result.get("mfg_date", "") or None,
        "mfg_date_normalized": result.get("mfg_date", "") or None,
        "exp_date_raw": exp_date or None,
        "exp_date_normalized": exp_date or None,
        "parsed_expiry_date": parsed_date,
        "expiry_status": status,
        "status_display": result.get("status_display", "EXPIRY UNKNOWN"),
        "confidence": result.get("confidence", 0.0),
        "message": result.get("message", ""),
        "warnings": warnings
    }
