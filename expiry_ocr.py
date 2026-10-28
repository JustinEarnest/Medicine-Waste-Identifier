from pathlib import Path
import re
import cv2
import easyocr
import numpy as np
from ultralytics import YOLO

MODEL_PATH = Path(
    r"runs/detect/medicine_waste/roboflow_v1/weights/best.pt"
)
IMAGE_DIR = Path(r"dataset/roboflow_export/test/images")
OUTPUT_DIR = Path(r"runs/expiry_ocr_v2")

CONFIDENCE = 0.25
IMAGE_SIZE = 512

# Common expiry-related labels and date formats.
EXP_LABEL = re.compile(
    r"\b(?:EXP|EXP\.?\s*DATE|DATE\s*EXP|EXPIRY|EXPIRATION|"
    r"USE\s*BEFORE|USE\s*BY|BEST\s*BEFORE|BBE)\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b("
    r"(?:0?[1-9]|1[0-2])\s*[/.-]\s*(?:20)?\d{2}"
    r"|"
    r"(?:0?[1-9]|[12]\d|3[01])\s*[/.-]\s*(?:0?[1-9]|1[0-2])"
    r"\s*[/.-]\s*\d{2,4}"
    r"|"
    r"(?:20\d{2})\s*[/.-]\s*(?:0?[1-9]|1[0-2])"
    r")\b"
)


def preprocess_variants(crop):
    """Create OCR-friendly grayscale, contrast, and threshold variants."""
    if crop is None or crop.size == 0:
        return {}

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop.copy()

    # Enlarge small printed text without excessive CPU/memory cost.
    enlarged = cv2.resize(
        gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(enlarged)
    threshold = cv2.adaptiveThreshold(
        contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )
    return {"gray": enlarged, "contrast": contrast, "threshold": threshold}


def recognize_crop(reader, crop):
    """Try four orientations and three preprocessing variants; rank useful OCR."""
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
            detections = reader.readtext(
                processed, detail=1, paragraph=False, decoder="greedy"
            )
            text_parts = [
                item[1].strip() for item in detections if len(item) > 1 and item[1].strip()
            ]
            text = " ".join(text_parts)
            if not text:
                continue

            confidence_values = [
                float(item[2]) for item in detections
                if len(item) > 2 and isinstance(item[2], (int, float))
            ]
            average_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values else 0.0
            )

            # Prefer text containing expiry labels and plausible date-like strings.
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

    attempts.sort(key=lambda item: rank_ocr_attempt(item), reverse=True)
    return attempts[0], attempts



def rank_ocr_attempt(item):
    """Score OCR attempts for expiry-label and date usefulness."""
    text = item.get("text", "")
    upper = text.upper()
    score = float(item.get("confidence", 0.0))

    # Exact/common expiry words are stronger signals than raw OCR confidence.
    if re.search(r"\b(?:EXP|EXP\.|EXPIRY|EXPIRATION|DATE\s*EXP|EXP\s*DATE|USE\s*BY|USE\s*BEFORE|BEST\s*BEFORE|BBE)\b", upper):
        score += 1.25

    # OCR may split or confuse the short label; only a weak bonus.
    if re.search(r"\bEX[PPR]\b", upper):
        score += 0.25

    # Give a small bonus to date-like text, but never use this alone to confirm expiry.
    if re.search(r"(?<!\d)(?:0?[1-9]|1[0-2])\s*[/.-]\s*(?:20)?\d{2}(?!\d)", upper):
        score += 0.20
    if re.search(r"(?<!\d)(?:0[1-9]|1[0-2])0?20\d{2}(?!\d)", upper):
        score += 0.20

    # A strong manufacturing label without an expiry label is not a useful expiry candidate.
    if re.search(r"\b(?:MFG|MFD|FAB|MANUFACTURED)\b", upper) and not EXP_LABEL.search(upper):
        score -= 0.35

    return score


def find_expiry_date(text):
    """Extract expiry date only from EXP-related labels, never from MFG/MFD/FAB."""
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
        return None

    after_label = normalized[expiry_match.end():]
    next_label = re.search(
        r"\b(?:MFG|MFD|FAB|MANUFACTURED|MANUFACTURING|LOT|BATCH|B\.?\s*NO|"
        r"EXP|EXPIRY|EXPIRATION|USE\s*BY|USE\s*BEFORE|BEST\s*BEFORE|PER)\b",
        after_label,
    )
    if next_label:
        after_label = after_label[:next_label.start()]
    return parse_date(after_label)


def find_manufacturing_date(text):
    """Extract MFG/MFD/FAB date separately; never label it as expiry."""
    if not text:
        return None
    normalized = text.upper().replace("：", ":")
    normalized = re.sub(r"\bMFG[.]?\s*DATE\b", "MFG", normalized)
    normalized = re.sub(r"\bMFD[.]?\s*DATE\b", "MFD", normalized)
    normalized = re.sub(r"\bFAB[.]?\s*DATE\b", "FAB", normalized)
    normalized = re.sub(r"\bMANUFACTUR(?:E|ED|ING)\s*DATE\b", "MFG", normalized)
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
    return parse_date(after_label)


def parse_date(text):
    """Parse common medicine-label date formats; all results need verification."""
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
        return f"{month_names[match.group(1)]:02d}/{int(match.group(2))} [VERIFY]"

    match = re.search(
        r"(?<!\d)(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2}|\d{2})(?!\d)",
        text,
    )
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        if year < 100:
            year += 2000
        if 2000 <= year <= 2099:
            return f"{month:02d}/{year:04d} [VERIFY]"

    match = re.search(r"(?<!\d)(0[1-9]|1[0-2])(20\d{2})(?!\d)", text)
    if match:
        return f"{int(match.group(1)):02d}/{int(match.group(2)):04d} [VERIFY]"

    match = re.search(r"(?<!\d)(0[1-9]|1[0-2])0(20\d{2})(?!\d)", text)
    if match:
        return f"{int(match.group(1)):02d}/{int(match.group(2)):04d} [VERIFY OCR]"

    match = re.search(r"(?<!\d)(0[1-9]|1[0-2])\d(20\d{2})(?!\d)", text)
    if match:
        return f"{int(match.group(1)):02d}/{int(match.group(2)):04d} [VERIFY OCR - AMBIGUOUS]"
    return None


def find_all_dates(text):
    """Find ordinary date candidates without assigning their meaning."""

    patterns = [
        r"(?<!\d)(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2}|\d{2})(?!\d)",
        r"(?<!\d)(0[1-9]|1[0-2])(20\d{2})(?!\d)",
    ]

    dates = []

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            month = int(match.group(1))
            year = int(match.group(2))

            if year < 100:
                year += 2000

            if 2000 <= year <= 2099:
                candidate = f"{month:02d}/{year:04d}"

                if candidate not in dates:
                    dates.append(candidate)

    return dates

def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH.resolve()}"
        )

    if not IMAGE_DIR.is_dir():
        raise FileNotFoundError(
            f"Image folder not found: {IMAGE_DIR.resolve()}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crops_dir = OUTPUT_DIR / "crops"
    crops_dir.mkdir(exist_ok=True)

    print("Loading YOLOv8...")
    model = YOLO(str(MODEL_PATH))

    print("Loading EasyOCR...")
    reader = easyocr.Reader(["en"], gpu=False)

    images = sorted(
        p for p in IMAGE_DIR.iterdir()
        if p.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp"
        }
    )

    report_path = OUTPUT_DIR / "results.txt"

    with report_path.open("w", encoding="utf-8") as report:
        for image_path in images:
            image = cv2.imread(str(image_path))

            if image is None:
                continue

            prediction = model.predict(
                source=image,
                imgsz=IMAGE_SIZE,
                conf=CONFIDENCE,
                verbose=False,
            )[0]

            report.write(f"\nIMAGE: {image_path.name}\n")
            print(f"\nImage: {image_path.name}")

            if prediction.boxes is None or len(prediction.boxes) == 0:
                print("  No detected region.")
                report.write("  No detected region.\n")
                continue

            for index, box in enumerate(prediction.boxes, start=1):
                x1, y1, x2, y2 = map(
                    int, box.xyxy[0].cpu().tolist()
                )

                height, width = image.shape[:2]

                # Add extra margin to preserve the complete medicine label.
                box_width = x2 - x1
                box_height = y2 - y1

                pad_x = int(box_width * 0.15)
                pad_y = int(box_height * 0.25)

                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)
                x2 = min(width, x2 + pad_x)
                y2 = min(height, y2 + pad_y)

                crop = image[y1:y2, x1:x2]

                if crop.size == 0:
                    continue

                crop_path = crops_dir / (
                    f"{image_path.stem}_region_{index}.jpg"
                )
                cv2.imwrite(str(crop_path), crop)

                best, attempts = recognize_crop(reader, crop)

                # Save all OCR attempts to a separate diagnostic report.
                # This helps compare rotations/preprocessing when the chosen text is poor.
                if attempts:
                    attempts_path = OUTPUT_DIR / "ocr_attempts.txt"
                    with attempts_path.open("a", encoding="utf-8") as attempts_report:
                        attempts_report.write(f"\nIMAGE: {image_path.name} | REGION: {index}\n")
                        for attempt in sorted(attempts, key=lambda item: rank_ocr_attempt(item), reverse=True):
                            attempts_report.write(
                                f"  score={rank_ocr_attempt(attempt):.3f} "
                                f"conf={attempt['confidence']:.3f} "
                                f"rotation={attempt['rotation']} method={attempt['method']} "
                                f"text={attempt['text']}\\n"
                            )

                if best:
                    text = best["text"]

                    # Extract manufacturing and expiry dates independently.
                    # OCR-derived dates remain candidates until manually verified.
                    manufacturing_date = find_manufacturing_date(text)
                    expiry_date = find_expiry_date(text)

                    print(
                        f"  Region {index}: {text} "
                        f"(OCR confidence={best['confidence']:.2f}, "
                        f"rotation={best['rotation']}, "
                        f"method={best['method']})"
                    )

                    if manufacturing_date:
                        print(
                            f"    Manufacturing-date candidate: "
                            f"{manufacturing_date}"
                        )
                    else:
                        print("    Manufacturing date: NOT CONFIRMED")

                    if expiry_date:
                        print(f"    Expiry-date candidate: {expiry_date}")
                    else:
                        print("    Expiry date: NOT CONFIRMED")

                    report.write(
                        f"  Region {index}: {text}\\n"
                        f"    OCR confidence: "
                        f"{best['confidence']:.3f}\\n"
                        f"    Rotation: {best['rotation']}\\n"
                        f"    Preprocessing: {best['method']}\\n"
                        f"    Manufacturing candidate: "
                        f"{manufacturing_date or 'NOT CONFIRMED'}\\n"
                        f"    Expiry candidate: "
                        f"{expiry_date or 'NOT CONFIRMED'}\\n"
                    )
                else:
                    print(f"  Region {index}: No readable text")
                    report.write(
                        f"  Region {index}: No readable text\n"
                    )

    print(f"\nFinished. Results saved to: {report_path.resolve()}")
    print(f"Saved crops to: {crops_dir.resolve()}")


if __name__ == "__main__":
    main()