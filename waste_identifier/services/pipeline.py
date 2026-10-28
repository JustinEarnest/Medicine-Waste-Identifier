import os
from pathlib import Path
import re
from datetime import date
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
import easyocr
from ultralytics import YOLO

from expiry_status import classify_expiry, parse_expiry_date

# Define Model paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "runs" / "detect" / "medicine_waste" / "roboflow_v1" / "weights" / "best.pt"
FALLBACK_MODEL_PATH = BASE_DIR / "yolov8n.pt"

# Global Singletons for fast repeated inference
_YOLO_MODEL = None
_EASYOCR_READER = None


def get_yolo_model():
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        if MODEL_PATH.is_file():
            _YOLO_MODEL = YOLO(str(MODEL_PATH))
        elif FALLBACK_MODEL_PATH.is_file():
            _YOLO_MODEL = YOLO(str(FALLBACK_MODEL_PATH))
        else:
            _YOLO_MODEL = YOLO("yolov8n.pt")
    return _YOLO_MODEL


def get_ocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        # Initialized once on CPU for safety across environments
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
    return _EASYOCR_READER


EXP_LABEL = re.compile(
    r"\b(?:EXP|EXP\.?\s*DATE|DATE\s*EXP|EXPIRY|EXPIRATION|"
    r"USE\s*BEFORE|USE\s*BY|BEST\s*BEFORE|BBE)\b",
    re.IGNORECASE,
)


def preprocess_variants(crop: np.ndarray) -> Dict[str, np.ndarray]:
    """Generates grayscale, CLAHE enhanced, and adaptive thresholded variants."""
    if crop is None or crop.size == 0:
        return {}

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop.copy()
    enlarged = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(enlarged)
    threshold = cv2.adaptiveThreshold(
        contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )
    return {"gray": enlarged, "contrast": contrast, "threshold": threshold}


def rank_ocr_attempt(item: Dict[str, Any]) -> float:
    text = item.get("text", "")
    upper = text.upper()
    score = float(item.get("confidence", 0.0))

    if re.search(r"\b(?:EXP|EXP\.|EXPIRY|EXPIRATION|DATE\s*EXP|EXP\s*DATE|USE\s*BY|USE\s*BEFORE|BEST\s*BEFORE|BBE)\b", upper):
        score += 1.25
    if re.search(r"\bEX[PPR]\b", upper):
        score += 0.25
    if re.search(r"(?<!\d)(?:0?[1-9]|1[0-2])\s*[/.-]\s*(?:20)?\d{2}(?!\d)", upper):
        score += 0.20
    if re.search(r"(?<!\d)(?:0[1-9]|1[0-2])0?20\d{2}(?!\d)", upper):
        score += 0.20
    if re.search(r"\b(?:MFG|MFD|FAB|MANUFACTURED)\b", upper) and not EXP_LABEL.search(upper):
        score -= 0.35

    return score


def recognize_crop(reader: easyocr.Reader, crop: np.ndarray) -> Tuple[Optional[Dict[str, Any]], list]:
    attempts = []
    if crop is None or crop.size == 0:
        return None, attempts

    rotations = (
        (0, crop.copy()),
        (90, cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)),
        (180, cv2.rotate(crop, cv2.ROTATE_180)),
        (270, cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    )

    for rotation, rotated in rotations:
        variants = preprocess_variants(rotated)
        for method, processed in variants.items():
            try:
                detections = reader.readtext(processed, detail=1, paragraph=False, decoder="greedy")
            except Exception:
                continue

            text_parts = [item[1].strip() for item in detections if len(item) > 1 and item[1].strip()]
            text = " ".join(text_parts)
            if not text:
                continue

            confidence_values = [
                float(item[2]) for item in detections if len(item) > 2 and isinstance(item[2], (int, float))
            ]
            average_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

            score = average_confidence
            if EXP_LABEL.search(text):
                score += 1.0
            if re.search(r"(?<!\d)(?:0?[1-9]|1[0-2])\s*[/.-]?\s*(?:20)?\d{2}(?!\d)", text):
                score += 0.15

            attempts.append({
                "text": text,
                "confidence": average_confidence,
                "rotation": rotation,
                "method": method,
                "score": score,
            })

    if not attempts:
        return None, attempts

    attempts.sort(key=rank_ocr_attempt, reverse=True)
    return attempts[0], attempts


def parse_date_candidate(text: str) -> Optional[str]:
    if not text:
        return None
    text = text.upper()
    month_names = {
        "JAN": 1, "JANUARY": 1, "FEB": 2, "FEBRUARY": 2,
        "MAR": 3, "MARCH": 3, "APR": 4, "APRIL": 4,
        "MAY": 5, "JUN": 6, "JUNE": 6, "JUL": 7, "JULY": 7,
        "AUG": 8, "AUGUST": 8, "SEP": 9, "SEPT": 9,
        "SEPTEMBER": 9, "OCT": 10, "OCTOBER": 10,
        "NOV": 11, "NOVEMBER": 11, "DEC": 12, "DECEMBER": 12,
    }
    month_pattern = (
        r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|"
        r"SEPTEMBER|SEPT|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|"
        r"APR|JUN|JUL|AUG|OCT|NOV|DEC)\s*[,.-]?\s*(20\d{2})\b"
    )
    match = re.search(month_pattern, text)
    if match:
        return f"{month_names[match.group(1)]:02d}/{int(match.group(2))}"

    match = re.search(r"(?<!\d)(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2}|\d{2})(?!\d)", text)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        if year < 100:
            year += 2000
        if 2000 <= year <= 2099:
            return f"{month:02d}/{year:04d}"

    match = re.search(r"(?<!\d)(0[1-9]|1[0-2])(20\d{2})(?!\d)", text)
    if match:
        return f"{int(match.group(1)):02d}/{int(match.group(2)):04d}"

    return None


def find_expiry_date(text: str) -> Optional[str]:
    if not text:
        return None
    normalized = text.upper().replace("：", ":")
    normalized = re.sub(r"\bEXPIRAT[Il1]ON\b", "EXPIRATION", normalized)
    normalized = re.sub(r"\bEXP[.]?\s*IRY(?:\s*DATE)?\b", "EXP", normalized)
    normalized = re.sub(r"\bEXP[.]?\s*DATE\b", "EXP", normalized)
    normalized = re.sub(r"\bDATE\s*EXP[.]?\b", "EXP", normalized)
    normalized = re.sub(r"\bUSE\s*B[E3]FORE\b", "USE BEFORE", normalized)
    normalized = re.sub(r"\bBEST\s*B[E3]FORE\b", "BEST BEFORE", normalized)

    expiry_pattern = (
        r"\bEXP\b|\bEXPIRY\b|\bEXPIRATION\b|"
        r"\bUSE\s*BEFORE\b|\bUSE\s*BY\b|"
        r"\bBEST\s*BEFORE\b|\bBBE\b"
    )
    expiry_match = re.search(expiry_pattern, normalized)
    if not expiry_match:
        # Fallback: check if standard date exists anywhere in text if EXP is missing
        return parse_date_candidate(normalized)

    after_label = normalized[expiry_match.end():]
    next_label = re.search(
        r"\b(?:MFG|MFD|FAB|MANUFACTURED|MANUFACTURING|LOT|BATCH|B\.?\s*NO|"
        r"EXP|EXPIRY|EXPIRATION|USE\s*BY|USE\s*BEFORE|BEST\s*BEFORE|PER)\b",
        after_label,
    )
    if next_label:
        after_label = after_label[:next_label.start()]
    return parse_date_candidate(after_label) or parse_date_candidate(normalized)


def find_manufacturing_date(text: str) -> Optional[str]:
    if not text:
        return None
    normalized = text.upper().replace("：", ":")
    normalized = re.sub(r"\bMFG[.]?\s*DATE\b", "MFG", normalized)
    normalized = re.sub(r"\bMFD[.]?\s*DATE\b", "MFD", normalized)
    normalized = re.sub(r"\bFAB[.]?\s*DATE\b", "FAB", normalized)
    match = re.search(r"\b(?:MFG|MFD|FAB|MANUFACTURED|MANUFACTURING)\b", normalized)
    if not match:
        return None
    after_label = normalized[match.end():]
    next_label = re.search(
        r"\b(?:MFG|MFD|FAB|MANUFACTURED|MANUFACTURING|LOT|BATCH|"
        r"EXP|EXPIRY|EXPIRATION|USE\s*BY|USE\s*BEFORE|BEST\s*BEFORE|PER)\b",
        after_label,
    )
    if next_label:
        after_label = after_label[:next_label.start()]
    return parse_date_candidate(after_label)


# Medicine Knowledge Base for Illness and Disposal Retrieval
MEDICINE_DB = {
    "PARACETAMOL": {
        "name": "Paracetamol (Acetaminophen)",
        "illness": "Analgesic and antipyretic: Used for mild-to-moderate pain (headache, toothache, muscle aches) and fever reduction.",
        "disposal": "Take-back program preferred. Household: Mix crushed or whole tablets with coffee grounds or cat litter in a sealed bag; throw in household trash. NEVER flush into toilet or sink.",
    },
    "AMOXICILLIN": {
        "name": "Amoxicillin",
        "illness": "Broad-spectrum penicillin antibiotic: Used to treat bacterial infections (respiratory, ear, throat, urinary tract).",
        "disposal": "CRITICAL HAZARD: Antibiotics in wastewater fuel antimicrobial resistance. Return to pharmacy take-back drop box. Do NOT discard down water drainage.",
    },
    "CETIRIZINE": {
        "name": "Cetirizine Hydrochloride",
        "illness": "Second-generation antihistamine: Relieves allergy symptoms such as sneezing, runny nose, itchy watery eyes, and hives.",
        "disposal": "Pharmacy take-back box recommended. If home disposal is necessary, seal inside an unappealing mixture in a sturdy plastic bag before household waste.",
    },
    "IBUPROFEN": {
        "name": "Ibuprofen",
        "illness": "Nonsteroidal anti-inflammatory drug (NSAID): Used for arthritis, menstrual cramps, dental pain, fever, and inflammation.",
        "disposal": "Toxic to aquatic organisms. Deposit in community drug take-back receptacle. Do not flush.",
    },
    "AZITHROMYCIN": {
        "name": "Azithromycin",
        "illness": "Macrolide antibiotic: Treats bacterial chest infections, tonsillitis, and skin infections.",
        "disposal": "High environmental concern. Hand over to hospital or pharmacy pharmaceutical collection kiosks.",
    },
    "PANTOPRAZOLE": {
        "name": "Pantoprazole",
        "illness": "Proton pump inhibitor (PPI): Decreases stomach acid; treats GERD, acid reflux, and peptic ulcers.",
        "disposal": "Seal blisters in non-transparent container with unpalatable waste before binning. Do not empty capsules into sink.",
    },
    "METFORMIN": {
        "name": "Metformin Hydrochloride",
        "illness": "Biguanide: First-line medication for the treatment of type 2 diabetes by lowering blood glucose levels.",
        "disposal": "Take-back drop-box preferred. Seal in child-resistant waste container before trash disposal.",
    },
}


def lookup_medicine_info(ocr_text: str) -> Tuple[str, str, str]:
    upper = ocr_text.upper()
    for key, data in MEDICINE_DB.items():
        if key in upper:
            return data["name"], data["illness"], data["disposal"]

    # Generic Smart Fallback
    default_name = "Pharmaceutical Strip / Packaging"
    default_illness = "Pharmaceutical formulation. Consult the product packaging or your healthcare professional for specific therapeutic indications."
    default_disposal = (
        "1. DO NOT FLUSH: Never dispose of medicines down toilets or sinks to protect groundwater.\n"
        "2. PHARMACY TAKE-BACK: Locate your nearest authorized pharmacy or hospital take-back drop box.\n"
        "3. TRASH DISPOSAL: If no take-back is accessible, mix the medication with unpalatable substance "
        "(coffee grounds or cat litter) in a sealed bag, and place in regular garbage. Remove all identifiable label info."
    )
    return default_name, default_illness, default_disposal


def process_medicine_image(
    image_input: Any,
    output_dir: Path,
    file_stem: str = "scan"
) -> Dict[str, Any]:
    """
    Executes the full pipeline:
    1. YOLOv8 label region detection
    2. Region cropping and image annotation
    3. Multi-orientation OCR extraction
    4. Manufacturing and expiry date parsing
    5. Expiry status classification
    6. Medical knowledge & disposal guidance retrieval
    """
    if isinstance(image_input, (str, Path)):
        image = cv2.imread(str(image_input))
    elif isinstance(image_input, np.ndarray):
        image = image_input
    else:
        raise ValueError("Unsupported image input type")

    if image is None:
        return {"success": False, "error": "Unable to read image."}

    height, width = image.shape[:2]
    annotated_image = image.copy()

    # 1. YOLOv8 Detection
    model = get_yolo_model()
    reader = get_ocr_reader()

    prediction = model.predict(source=image, imgsz=512, conf=0.15, verbose=False)[0]

    crop = None
    confidence = 0.0
    detected_box = None

    if prediction.boxes is not None and len(prediction.boxes) > 0:
        # Select best box
        best_box = max(prediction.boxes, key=lambda b: float(b.conf[0].cpu().item()))
        confidence = float(best_box.conf[0].cpu().item())
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().tolist())

        # Margin expansion
        box_w = x2 - x1
        box_h = y2 - y1
        pad_x = int(box_w * 0.15)
        pad_y = int(box_h * 0.25)
        x1_pad = max(0, x1 - pad_x)
        y1_pad = max(0, y1 - pad_y)
        x2_pad = min(width, x2 + pad_x)
        y2_pad = min(height, y2 + pad_y)

        crop = image[y1_pad:y2_pad, x1_pad:x2_pad]
        detected_box = (x1, y1, x2, y2)

        # Draw visual bounding box & badge on annotated image
        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (20, 190, 50), 3)
        label_text = f"Expiry Label ({confidence*100:.1f}%)"
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(annotated_image, (x1, max(0, y1 - 25)), (x1 + tw + 10, y1), (20, 190, 50), -1)
        cv2.putText(annotated_image, label_text, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    else:
        # Fallback to entire image if YOLO does not detect tight region
        crop = image.copy()
        confidence = 0.50

    # Save output artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_filename = f"{file_stem}_annotated.jpg"
    crop_filename = f"{file_stem}_crop.jpg"

    annotated_path = output_dir / annotated_filename
    crop_path = output_dir / crop_filename

    cv2.imwrite(str(annotated_path), annotated_image)
    cv2.imwrite(str(crop_path), crop if crop is not None else image)

    # 2. OCR Extraction
    best_attempt, all_attempts = recognize_crop(reader, crop)
    raw_ocr_text = best_attempt["text"] if best_attempt else ""
    ocr_confidence = best_attempt["confidence"] if best_attempt else 0.0

    # 3. Date Parsing
    mfg_candidate = find_manufacturing_date(raw_ocr_text)
    exp_candidate = find_expiry_date(raw_ocr_text)

    # 4. Status Classification
    classification = classify_expiry(exp_candidate)
    status_str = classification["status"]

    if status_str == "EXPIRED":
        db_status = "EXPIRED"
    elif status_str == "NOT EXPIRED":
        db_status = "VALID"
    else:
        db_status = "REVIEW"

    parsed_date_iso = classification.get("expiry_date")
    parsed_date_obj = date.fromisoformat(parsed_date_iso) if parsed_date_iso else None

    # 5. Medicine Name & Disposal lookup
    med_name, illness, disposal = lookup_medicine_info(raw_ocr_text)

    # Overall confidence is average of detection & OCR
    overall_confidence = (confidence + ocr_confidence) / 2 if ocr_confidence > 0 else confidence

    return {
        "success": True,
        "annotated_filename": annotated_filename,
        "crop_filename": crop_filename,
        "raw_ocr_text": raw_ocr_text,
        "mfg_date": mfg_candidate or "",
        "exp_date": exp_candidate or "",
        "parsed_expiry_date": parsed_date_obj,
        "status": db_status,
        "status_display": classification["status"],
        "confidence": round(overall_confidence, 3),
        "medicine_name": med_name,
        "illness_info": illness,
        "disposal_guidance": disposal,
        "message": classification["message"],
    }
