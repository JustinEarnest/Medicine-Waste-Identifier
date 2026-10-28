"""
Front-side medicine identification service.
Implements Phase 3 front packaging analysis with OpenAI Vision API and
local EasyOCR fallback (plan.md Section 5).
"""
import os
import re
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np

from .catalogue import match_catalogue, normalize_string

logger = logging.getLogger(__name__)

# Configurable OpenAI Model
DEFAULT_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

# EasyOCR reader singleton for fallback
_FRONT_OCR_READER = None


def get_front_ocr_reader():
    global _FRONT_OCR_READER
    if _FRONT_OCR_READER is None:
        import easyocr
        _FRONT_OCR_READER = easyocr.Reader(["en"], gpu=False)
    return _FRONT_OCR_READER


def encode_image_base64(image_path: Path) -> str:
    """Reads image file and converts to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def call_openai_vision(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Calls OpenAI Vision API with strict visible-text instructions.
    Returns structured dict or None if API key not available or request fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.info("OPENAI_API_KEY not configured. Falling back to local OCR engine.")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        base64_image = encode_image_base64(image_path)

        prompt = (
            "You are a medical packaging text recognition assistant. "
            "Inspect the provided front-side photograph of a medicine package. "
            "Only report text that is visibly printed on the package. "
            "DO NOT infer or guess the medicine name from package appearance or color. "
            "Return ONLY a valid JSON object with the following schema: \n"
            "{\n"
            '  "visible_medicine_name": "exact brand or product name if readable, else null",\n'
            '  "strength": "dosage strength such as 500mg or 625 Duo if readable, else null",\n'
            '  "dosage_form": "Tablet, Capsule, Syrup, Injection, etc. if readable, else null",\n'
            '  "manufacturer": "pharmaceutical company name if readable, else null",\n'
            '  "visible_text": ["array", "of", "all", "prominently", "visible", "words"],\n'
            '  "identity_status": "confirmed | unconfirmed | ambiguous",\n'
            '  "ambiguity_reason": "explanation if unconfirmed or ambiguous, else null"\n'
            "}"
        )

        response = client.chat.completions.create(
            model=DEFAULT_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            timeout=30.0
        )

        content = response.choices[0].message.content
        if content:
            parsed = json.loads(content)
            parsed["source"] = "openai_vision"
            parsed["model"] = DEFAULT_VISION_MODEL
            return parsed
    except Exception as e:
        logger.warning(f"OpenAI vision API call failed: {e}. Falling back to local OCR.")
        return None


def run_local_front_ocr(image_path: Path) -> Dict[str, Any]:
    """
    Local OCR fallback using EasyOCR to extract prominent medicine name,
    manufacturer, and visible text lines from the front of the package.
    """
    reader = get_front_ocr_reader()
    img = cv2.imread(str(image_path))
    if img is None:
        return {
            "visible_medicine_name": None,
            "strength": None,
            "dosage_form": None,
            "manufacturer": None,
            "visible_text": [],
            "identity_status": "unconfirmed",
            "ambiguity_reason": "Could not decode front image file.",
            "source": "local_ocr"
        }

    # Run OCR with details (bounding box, text, confidence)
    results = reader.readtext(img, detail=1, paragraph=False)

    visible_lines = []
    line_candidates = []

    for item in results:
        text = item[1].strip()
        conf = float(item[2])
        if not text or len(text) < 2:
            continue
        visible_lines.append(text)

        # Skip text lines that are clearly pure dates, prices, or batch labels
        upper = text.upper()
        if re.match(r'^(?:EXP|MFG|BATCH|B\.?NO|M\.?R\.?P|RS|PRICE|\d{2}[/.-]\d{2,4})', upper):
            continue

        bbox = item[0]
        # Approximate font height from bbox
        height = abs(bbox[2][1] - bbox[0][1])
        line_candidates.append({
            "text": text,
            "height": height,
            "confidence": conf
        })

    if not line_candidates:
        return {
            "visible_medicine_name": None,
            "strength": None,
            "dosage_form": None,
            "manufacturer": None,
            "visible_text": visible_lines,
            "identity_status": "unconfirmed",
            "ambiguity_reason": "No legible front packaging text detected.",
            "source": "local_ocr"
        }

    # Sort candidates by font height (brand names typically largest font on front)
    line_candidates.sort(key=lambda x: (x["height"], x["confidence"]), reverse=True)
    best_candidate = line_candidates[0]["text"]

    # Extract strength if present
    strength_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|%|iu))\b', " ".join(visible_lines), re.IGNORECASE)
    strength = strength_match.group(1) if strength_match else None

    # Detect dosage form
    dosage_form = None
    all_text = " ".join(visible_lines).upper()
    for form in ["TABLET", "CAPSULE", "SYRUP", "INJECTION", "SUSPENSION", "DROPS", "OINTMENT", "GEL", "INHALER"]:
        if form in all_text:
            dosage_form = form.title()
            break

    # Look for manufacturer markers like "Pvt Ltd", "Laboratories", "Pharma"
    manufacturer = None
    for line in visible_lines:
        if re.search(r'\b(?:Ltd|Limited|Pharma|Laboratories|Lab|Healthcare|Remedies)\b', line, re.IGNORECASE):
            manufacturer = line
            break

    return {
        "visible_medicine_name": best_candidate,
        "strength": strength,
        "dosage_form": dosage_form,
        "manufacturer": manufacturer,
        "visible_text": visible_lines,
        "identity_status": "unconfirmed",  # Will be updated after catalogue matching
        "ambiguity_reason": None,
        "source": "local_ocr"
    }


def identify_front_medicine(image_path: Path) -> Dict[str, Any]:
    """
    Main entry point for front-side medicine packaging identification.
    1. Attempts OpenAI Vision API if configured.
    2. Falls back to local EasyOCR extraction if needed.
    3. Performs deterministic & fuzzy catalogue matching against 11.8k Indian medicines.
    4. Enforces safety rule: returns 'unconfirmed' if evidence is insufficient or ambiguous.
    """
    # 1. Structured extraction
    extraction = call_openai_vision(image_path)
    if extraction is None:
        extraction = run_local_front_ocr(image_path)

    raw_name = extraction.get("visible_medicine_name")
    raw_mfr = extraction.get("manufacturer")
    raw_strength = extraction.get("strength")

    # 2. Catalogue matching
    catalogue_result = match_catalogue(
        candidate_name=raw_name,
        manufacturer=raw_mfr,
        strength=raw_strength
    )

    match_record = catalogue_result.get("match")
    catalogue_status = catalogue_result.get("status", "unconfirmed")
    catalogue_conf = catalogue_result.get("confidence", 0.0)

    # Combine extraction and catalogue evidence
    final_status = "unconfirmed"
    ambiguity_reason = None

    if catalogue_status == "confirmed" and match_record:
        final_status = "confirmed"
        final_name = match_record.get("name", raw_name)
        final_mfr = match_record.get("manufacturer", raw_mfr)
        final_composition = match_record.get("composition", "")
        final_uses = match_record.get("uses", "")
    elif catalogue_status == "ambiguous":
        final_status = "ambiguous"
        final_name = raw_name or "Unconfirmed Medicine"
        final_mfr = raw_mfr or "Unknown Manufacturer"
        final_composition = match_record.get("composition", "") if match_record else ""
        final_uses = match_record.get("uses", "") if match_record else ""
        ambiguity_reason = "Multiple catalogue candidates found. Please verify with physical package."
    else:
        final_status = "unconfirmed"
        final_name = raw_name or "Unconfirmed Medicine"
        final_mfr = raw_mfr or "Unknown Manufacturer"
        final_composition = ""
        final_uses = ""
        ambiguity_reason = catalogue_result.get("reason", "Visible text could not be verified in the catalogue.")

    return {
        "visible_medicine_name": final_name,
        "raw_candidate_name": raw_name,
        "strength": raw_strength or (match_record.get("strength") if match_record else None),
        "dosage_form": extraction.get("dosage_form") or (match_record.get("dosage_form") if match_record else None),
        "manufacturer": final_mfr,
        "composition": final_composition,
        "illness_uses": final_uses,
        "visible_text": extraction.get("visible_text", []),
        "catalogue_match": match_record,
        "catalogue_candidates": catalogue_result.get("candidates", []),
        "catalogue_confidence": catalogue_conf,
        "identity_status": final_status,
        "ambiguity_reason": ambiguity_reason,
        "extraction_source": extraction.get("source", "unknown"),
        "model_used": extraction.get("model", "easyocr_local")
    }
