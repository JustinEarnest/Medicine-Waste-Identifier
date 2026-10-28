# Medicine Waste Identifier — Complete Project Roadmap

**Project:** Medicine Waste Identifier  
**Current focus:** Computer Vision, medicine-label detection, OCR date extraction, expiry-status estimation  
**Primary stack:** Python, YOLOv8 (Ultralytics), OpenCV, EasyOCR, PyTorch  
**Planned web stack:** Django + FastAPI + HTML/CSS/JavaScript  
**Dataset source:** Roboflow export  
**Document purpose:** End-to-end guide from the current OCR phase through final application, testing, documentation, and demonstration.

> **Important project limitation:** This system is a prototype to assist label reading. OCR can misread dates, and a detected date does not establish that a medicine is safe to use. Every extracted date must be checked against the original package. Do not use the prototype as a substitute for a pharmacist or clinician.

---

## 1. Project Overview

Medicine Waste Identifier is a computer-vision project intended to detect medicine expiry-label regions, read visible manufacturing and expiry date text, and present a preliminary expiry-status estimate. The planned application combines object detection, OCR, date parsing, a web interface, and an API.

### Main objectives

1. Detect medicine expiry-label regions in uploaded or test images.
2. Extract manufacturing-date labels such as `MFG`, `MFD`, or `FAB`.
3. Extract expiry-date labels such as `EXP`, `EXP DATE`, `EXPIRY`, `USE BEFORE`, or `BEST BEFORE`.
4. Parse supported date formats and estimate whether the stated expiry date has passed.
5. Show uncertain or unreadable results as **EXPIRY UNKNOWN** rather than guessing.
6. Save results for testing and demonstrate the complete workflow through a web application.

### Current known project setup

The project has previously used these paths:

```text
runs/detect/medicine_waste/roboflow_v1/weights/best.pt
dataset/roboflow_export/test/images
```

The Roboflow export was reported to use one class:

```yaml
nc: 1
names: ['Medicine-expdate']
```

The dataset was previously described as having 1,088 raw images, with 133 label files in an earlier export/check. These counts may refer to different dataset stages; recount the current folders before reporting final dataset statistics.

---

## 2. Phase Roadmap

| Phase | Name | Main outcome | Status |
|---|---|---|---|
| A | Dataset collection and organization | Raw, selected, rejected, and duplicate image folders | In progress / verify current state |
| B | Dataset annotation and export | Roboflow annotations and YOLO dataset export | Export previously created; verify quality |
| C | Environment and model setup | Python environment, dependencies, YOLO weights | Previously configured; verify locally |
| D | OCR date extraction | Manufacturing and expiry date candidates | Script created; needs real-image validation |
| E | Expiry-status logic | EXPIRED / NOT EXPIRED / EXPIRY UNKNOWN | Standalone utility created |
| F | Integrated inference pipeline | YOLO + OCR + date parsing + report | Prototype script created; needs execution testing |
| G | Backend API | FastAPI inference endpoint | Planned |
| H | Web application | Django pages and image-upload workflow | Planned |
| I | Integration and user interface | Django frontend connected to FastAPI | Planned |
| J | Testing and evaluation | Metrics, error handling, edge cases | Planned |
| K | Final documentation and demo | Report, screenshots, presentation, demo checklist | Planned |

The phases are a practical roadmap, not a claim that all components have already been completed. Mark each phase complete only after testing it.

---

## 3. Phase A — Dataset Collection and Organization

### Goal
Prepare a clean and traceable set of medicine-package images.

### Suggested folder structure

```text
dataset/
├── raw_images/
├── selected_images/
├── rejected_images/
├── duplicates/
└── roboflow_export/
```

### Workflow

1. Collect images with readable medicine labels and varied lighting, angles, and packaging.
2. Keep original images unchanged in `raw_images/`.
3. Move suitable images to `selected_images/`.
4. Move blurry, unreadable, irrelevant, or unusable images to `rejected_images/`.
5. Store duplicate images in `duplicates/` rather than labeling the same image repeatedly.
6. Keep a record of image counts and the reason images were rejected.
7. Avoid publishing private information visible in photos, such as personal names, prescription details, or contact information.

### Completion checklist

- [ ] Image sources and permitted use documented.
- [ ] Duplicates checked.
- [ ] Rejected images separated.
- [ ] Dataset counts recorded.
- [ ] Train/validation/test split planned to avoid near-duplicate leakage.

---

## 4. Phase B — Annotation and Roboflow Export

### Goal
Label the visible expiry-date/medicine-label region for object detection.

### Current known export configuration

```yaml
train: ../train/images
val: ../valid/images
test: ../test/images

nc: 1
names: ['Medicine-expdate']
```

This example reflects the previously reported export. Always use the `data.yaml` supplied with the actual export and confirm that the paths are valid relative to that file.

### Annotation guidance

1. Draw a bounding box around the intended label region.
2. Keep the label definition consistent across images.
3. Include enough surrounding text to capture the date label and its value.
4. Avoid boxes that cut off `MFG`, `MFD`, `EXP`, or the printed date.
5. Review a sample of annotations before training.
6. Keep the test split separate from training and tuning.

### Important distinction

YOLO detects a region. It does **not** itself understand which printed date is the expiry date. OCR and date-label parsing are separate steps.

### Completion checklist

- [ ] `data.yaml` exists.
- [ ] Train/validation/test image folders exist.
- [ ] Label files match the intended images.
- [ ] Sample annotations visually checked.
- [ ] Class name and class count match the dataset.
- [ ] Dataset split avoids duplicate or near-duplicate leakage.

---

## 5. Phase C — Environment and Model Setup

### Goal
Run the model and OCR pipeline from the project's Python virtual environment.

### Example Windows PowerShell commands

Run from the project root:

```powershell
cd "C:\Users\VICTUS\OneDrive\Desktop\Medicine-Waste-Identifier"
.\venv\Scripts\Activate.ps1
python --version
python -m pip --version
```

If the virtual environment does not exist, create it with the Python installation appropriate for the project:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install project dependencies using the project's maintained requirements file when available:

```powershell
python -m pip install -r requirements.txt
```

If you need to install the core computer-vision dependencies individually:

```powershell
python -m pip install ultralytics opencv-python easyocr torch torchvision numpy pillow
```

Do not repeatedly reinstall packages if they are already installed. Confirm imports first:

```powershell
python -c "import cv2, easyocr, torch; import ultralytics; print('OpenCV:', cv2.__version__); print('PyTorch:', torch.__version__); print('Ultralytics import OK')"
```

### Model and dataset paths

The integrated prototype expects:

```text
runs/detect/medicine_waste/roboflow_v1/weights/best.pt
dataset/roboflow_export/test/images/
```

If your actual paths differ, edit the path constants at the top of the script. Use relative paths from the project root consistently.

### Completion checklist

- [ ] Virtual environment activates.
- [ ] Dependencies import successfully.
- [ ] Model weights exist.
- [ ] Test-image folder exists and contains images.
- [ ] One YOLO inference runs without error.
- [ ] Package versions recorded for reproducibility.

---

## 6. Phase D — OCR Date Extraction

### Goal
Read date text from the detected label region.

### Labels to recognize

**Manufacturing-related labels**
- `MFG`
- `MFD`
- `MFG DATE`
- `MFD DATE`
- `MANUFACTURED`
- `MANUFACTURING DATE`
- `FAB`

**Expiry-related labels**
- `EXP`
- `EXP DATE`
- `EXPIRY`
- `EXPIRY DATE`
- `EXPIRATION`
- `USE BEFORE`
- `BEST BEFORE`
- `BBE`

Packaging formats vary, and OCR may confuse letters or digits. The label and date must be parsed together so the manufacturing date is not mistaken for the expiry date.

### Current script

```text
expiry_ocr_mfg_exp_formats.py
```

A later integrated prototype was also created:

```text
expiry_ocr_integrated.py
```

The integrated script uses YOLO to detect regions, then EasyOCR with a small set of image preprocessing and rotation attempts. It attempts to extract MFG/MFD and EXP candidates and writes a report.

### Run the integrated prototype

```powershell
python expiry_ocr_integrated.py
```

Expected output location:

```text
runs/expiry_ocr_integrated/
├── results.txt
└── crops/
```

### Validation procedure

1. Run against a small set of test images first.
2. Compare OCR text with the actual printed package.
3. Check whether MFG/MFD and EXP labels are assigned correctly.
4. Record false detections, missed dates, and ambiguous OCR.
5. Do not treat the best OCR confidence score as proof that the date is correct.
6. If the date is not clearly associated with an expiry label, return **EXPIRY UNKNOWN**.

### Known limitations

- Rotated, curved, reflective, faded, or tiny text may fail.
- OCR can change `O` to `0`, `I` to `1`, or omit separators.
- Date parsing may not cover every regional or manufacturer-specific format.
- The current prototype is not guaranteed to extract every format and has not been validated on all images.

### Completion checklist

- [ ] OCR text is saved.
- [ ] Cropped label regions are saved.
- [ ] MFG/MFD and EXP candidates are displayed separately.
- [ ] OCR results manually checked on a representative sample.
- [ ] Unreadable and ambiguous dates remain unknown.
- [ ] Extraction accuracy is measured on manually verified labels.

---

## 7. Phase E — Expiry-Status Logic

### Goal
Classify a successfully parsed expiry-date candidate.

### Intended statuses

| Status | Meaning |
|---|---|
| `EXPIRED` | Parsed expiry date is earlier than the current date |
| `NOT EXPIRED` | Parsed expiry date is today or later |
| `EXPIRY UNKNOWN` | Missing, unreadable, ambiguous, or unsupported expiry date |

For an expiry label that contains only `MM/YYYY`, the prototype treats the stated month as valid through its final calendar day. This convention must be documented and confirmed against the applicable product labeling and requirements before production use.

### Standalone utility

```text
expiry_status.py
```

Run it with:

```powershell
python expiry_status.py
```

### Important safeguards

- Always display the original OCR candidate.
- Require manual verification of OCR-derived dates.
- Never infer an expiry date from the manufacturing date unless a valid, product-specific shelf-life rule is available and authorized.
- Do not claim that `NOT EXPIRED` means a medicine is safe to use; storage conditions, package integrity, recalls, and other factors matter.
- Use `EXPIRY UNKNOWN` when parsing fails.

### Completion checklist

- [ ] Month/year dates parse correctly.
- [ ] Full numeric dates parse correctly where supported.
- [ ] Invalid dates are rejected.
- [ ] Past, current, and future date cases tested.
- [ ] Missing and ambiguous dates return unknown.
- [ ] OCR uncertainty is clearly visible to the user.

---

## 8. Phase F — Integrated Inference Pipeline

### Goal
Combine detection, OCR, date extraction, and status classification in one workflow.

### Current prototype

```text
expiry_ocr_integrated.py
```

### Run

```powershell
python expiry_ocr_integrated.py
```

### Intended data flow

```text
Input image
    |
    v
YOLOv8 detects medicine-expiry label region
    |
    v
Crop detected region
    |
    v
Image preprocessing + EasyOCR
    |
    v
Recognized text
    |
    +----------------------+
    |                      |
    v                      v
MFG/MFD date parser    EXP date parser
                           |
                           v
                    Expiry status logic
                           |
                           v
             Console result + saved report
```

### Output

```text
runs/expiry_ocr_integrated/
├── results.txt
└── crops/
```

### Integration test

Run the script on several images with known, manually verified labels. Confirm that:
- a region is detected where expected;
- OCR text is captured;
- the expiry candidate comes from the expiry-related field;
- unknown results are not silently classified;
- output files are created;
- unreadable images are skipped safely.

### Completion checklist

- [ ] Script starts from project root.
- [ ] YOLO model loads.
- [ ] EasyOCR initializes.
- [ ] At least one test image is processed end-to-end.
- [ ] Report and crops are saved.
- [ ] Errors are handled and documented.
- [ ] Results manually checked before proceeding.

---

## 9. Phase G — FastAPI Inference API

### Goal
Expose the inference pipeline through an HTTP API so a frontend can submit an image and receive structured results.

### Planned endpoint

```text
POST /predict
```

Request: multipart form upload with an image file.

Example response structure:

```json
{
  "filename": "medicine_sample.jpg",
  "detections": [
    {
      "region": 1,
      "recognized_text": "MFG 10/2024 EXP 10/2026",
      "manufacturing_date_candidate": "10/2024",
      "expiry_date_candidate": "10/2026",
      "expiry_status": "NOT EXPIRED",
      "requires_manual_verification": true
    }
  ],
  "message": "OCR dates are candidates and must be checked against the package."
}
```

This is a proposed response format, not a response currently emitted by the existing script.

### Suggested API requirements

- Validate file type and size.
- Reject empty or corrupt uploads.
- Use a temporary upload directory and clean up temporary files.
- Return JSON with consistent fields.
- Return `EXPIRY UNKNOWN` for missing or ambiguous dates.
- Avoid returning raw server paths or sensitive exception details.
- Load model weights once during application startup, rather than once per request.
- Add clear HTTP error responses.
- Avoid concurrent model calls until thread/process behavior has been tested.

### Development server

After creating and implementing the FastAPI module, a typical local command may look like:

```powershell
uvicorn app.main:app --reload
```

The exact command depends on the final module structure and should be updated to match the actual code.

### Completion checklist

- [ ] `/health` or equivalent health endpoint works.
- [ ] `/predict` accepts a valid image.
- [ ] Invalid uploads return clear errors.
- [ ] JSON fields are consistent.
- [ ] Inference is not reinitialized for every request.
- [ ] API is tested locally.

---

## 10. Phase H — Django Web Application

### Goal
Provide a user-friendly website to upload an image and review the result.

### Planned pages

1. **Home page** — project introduction and upload button.
2. **Upload page** — image selection and validation.
3. **Results page** — image preview, detected region, OCR text, date candidates, status, and verification warning.
4. **History page** — optional list of previous results, if persistence is implemented.
5. **About / limitations page** — explain the prototype's intended use and limitations.

### Proposed user flow

```text
Open website
    |
    v
Select or capture medicine image
    |
    v
Django validates upload
    |
    v
Django sends image to FastAPI
    |
    v
FastAPI returns structured inference result
    |
    v
Django displays result page
```

### UI requirements

- Make the status text readable and accessible; do not rely on color alone.
- Display manufacturing and expiry candidates separately.
- Show the recognized OCR text for comparison.
- Clearly label results as automated estimates.
- Show `EXPIRY UNKNOWN` prominently when confidence is insufficient.
- Explain that users must verify the original package.
- Handle slow inference and upload errors gracefully.

### Completion checklist

- [ ] Django project and app created.
- [ ] Upload form implemented.
- [ ] File validation implemented.
- [ ] Django-to-FastAPI request implemented.
- [ ] Results template implemented.
- [ ] Error states and loading state implemented.
- [ ] Privacy and retention behavior documented.

---

## 11. Phase I — Backend and Frontend Integration

### Goal
Connect Django, FastAPI, and the computer-vision pipeline.

### Suggested responsibility split

| Component | Responsibility |
|---|---|
| Django | Pages, upload form, sessions, optional result history |
| FastAPI | Inference API and JSON response |
| YOLOv8 | Label-region detection |
| EasyOCR | Text recognition |
| Date parser | Extract and normalize date candidates |
| Status classifier | Estimate expiry status |
| Storage layer | Optional result metadata, subject to privacy requirements |

### Integration checks

- [ ] API base URL configured outside source code where appropriate.
- [ ] Django handles API timeouts and errors.
- [ ] Invalid JSON or unavailable API produces a friendly error.
- [ ] Uploaded images are not retained longer than necessary.
- [ ] Large images are resized or constrained safely.
- [ ] Frontend clearly shows uncertain results.
- [ ] The system does not claim to identify a medicine unless that feature is actually implemented.

---

## 12. Phase J — Testing and Evaluation

### Goal
Measure the system rather than relying only on a few successful examples.

### Test categories

**Dataset/model**
- Precision, recall, and mAP for label-region detection.
- Missed detections and false detections.
- Performance on different sizes, lighting, angles, and packaging.

**OCR**
- Exact text match or character error rate on a manually transcribed test set.
- Manufacturing-label extraction accuracy.
- Expiry-label extraction accuracy.
- Date normalization accuracy.

**Expiry classification**
- Correct status on manually verified expiry dates.
- Correct handling of month/year labels.
- Invalid and ambiguous date cases.
- Boundary cases: last day of the expiry month and first day after it.

**Web/API**
- Valid image upload.
- Unsupported file type.
- Oversized image.
- Corrupt image.
- No detected label.
- No readable text.
- Missing expiry label.
- API timeout or service unavailable.
- Multiple detections in one image.

### Evaluation spreadsheet columns

```text
image_id
ground_truth_label_present
detected_label_present
ground_truth_mfg
predicted_mfg
ground_truth_exp
predicted_exp
ground_truth_status
predicted_status
ocr_text_correct
date_extraction_correct
notes
```

Use a held-out test set. Do not tune the system against the test set and then report that same set as an independent final evaluation.

### Completion checklist

- [ ] Test set manually labeled.
- [ ] Detection metrics computed.
- [ ] OCR/date extraction metrics computed.
- [ ] Expiry-status errors reviewed.
- [ ] API and UI edge cases tested.
- [ ] Limitations reported honestly.

---

## 13. Phase K — Final Documentation and Demonstration

### Final deliverables

- [ ] Source code and `requirements.txt`.
- [ ] Dataset description and annotation process.
- [ ] Model training configuration and weights location.
- [ ] OCR and date-parsing explanation.
- [ ] Architecture diagram.
- [ ] API endpoint documentation.
- [ ] Screenshots of upload and results pages.
- [ ] Test cases and evaluation results.
- [ ] Known limitations and future improvements.
- [ ] Setup and run instructions.
- [ ] Short demonstration video or live demo.
- [ ] Final project report and presentation slides, if required by the college.

### Suggested demo sequence

1. Start FastAPI.
2. Start Django.
3. Open the application in a browser.
4. Upload a clear medicine label image.
5. Show the detected label region.
6. Show the OCR text and manufacturing/expiry candidates.
7. Show the expiry-status estimate.
8. Demonstrate an unreadable or ambiguous example returning `EXPIRY UNKNOWN`.
9. Explain manual verification and system limitations.
10. Show the evaluation summary.

### Suggested final report chapters

1. Introduction
2. Problem statement and objectives
3. Existing system and proposed system
4. Literature review (with cited sources, if required)
5. Requirements and technology stack
6. System architecture and workflow
7. Dataset collection and annotation
8. Model and OCR implementation
9. API and web application
10. Testing and evaluation
11. Results and discussion
12. Limitations and future scope
13. Conclusion
14. References
15. Appendix: setup commands and selected code

Do not invent performance values. Add only metrics obtained from actual experiments.

---

## 14. Recommended Project Structure

The following is a target structure. It is a recommendation, not a statement that every file already exists.

```text
Medicine-Waste-Identifier/
├── dataset/
│   ├── raw_images/
│   ├── selected_images/
│   ├── rejected_images/
│   ├── duplicates/
│   └── roboflow_export/
├── runs/
│   └── detect/
│       └── medicine_waste/
│           └── roboflow_v1/
│               └── weights/
│                   └── best.pt
├── vision/
│   ├── __init__.py
│   ├── detector.py
│   ├── ocr.py
│   ├── date_parser.py
│   └── expiry_status.py
├── api/
│   └── main.py
├── web/
│   ├── manage.py
│   └── ...
├── tests/
│   ├── test_date_parser.py
│   ├── test_expiry_status.py
│   └── test_api.py
├── expiry_ocr_mfg_exp_formats.py
├── expiry_status.py
├── expiry_ocr_integrated.py
├── requirements.txt
├── README.md
└── .gitignore
```

You do not need to reorganize the entire project immediately. First get the current integrated script running, then refactor gradually.

---

## 15. Common Troubleshooting

### Model file not found

Check:

```powershell
Test-Path .\runs\detect\medicine_waste\roboflow_v1\weights\best.pt
```

If it returns `False`, locate the actual `best.pt` and update `MODEL_PATH`.

### Test-image folder not found

Check:

```powershell
Test-Path .\dataset\roboflow_export\test\images
Get-ChildItem .\dataset\roboflow_export\test\images
```

Update `IMAGE_DIR` if the extracted Roboflow dataset uses another path.

### Missing Python package

Activate the correct virtual environment and install from `requirements.txt`. Check imports before reinstalling everything.

### OCR does not detect a date

- Inspect the saved crop.
- Check whether the printed date is legible.
- Check whether the expiry label and value are both inside the crop.
- Try better lighting, a higher-resolution photo, or a tighter camera angle.
- Keep the result unknown if the date cannot be verified.

### Incorrect date selected

- Compare the full OCR text with the package.
- Check whether the parser confused MFG/MFD with EXP.
- Add the format to a unit-tested parser only after confirming it appears in the dataset.
- Never assume that the latest-looking date is always the expiry date.

### Git and large files

- Avoid committing virtual environments and generated cache folders.
- Review the repository before pushing images or model weights.
- Respect dataset licenses and avoid committing private or sensitive images.
- Use `.gitignore` for local environments, temporary files, and outputs when appropriate.

Example `.gitignore` entries:

```gitignore
venv/
__pycache__/
*.py[cod]
.env
runs/expiry_ocr_integrated/
```

Whether to commit trained model weights or dataset files depends on their size, licensing, and project requirements.

---

## 16. Immediate Next Actions

Follow this order rather than building every layer at once:

1. Run `python expiry_ocr_integrated.py`.
2. Confirm the model and test-image paths work.
3. Inspect `runs/expiry_ocr_integrated/results.txt` and the saved crops.
4. Manually verify a representative set of MFG/MFD and EXP candidates.
5. Fix date extraction errors and add tests.
6. Finalize the integrated inference function.
7. Build and test the FastAPI endpoint.
8. Build the Django upload/results interface.
9. Connect Django to FastAPI.
10. Run the complete evaluation and prepare the final report/demo.

**Definition of done:** The project is ready for final demonstration only when the full upload-to-results flow has been tested, its evaluation is documented, and uncertain OCR outputs are handled safely.
