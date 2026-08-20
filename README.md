# 💊 Vision-Based Smart Medicine Waste Identifier

> A computer-vision and AI-powered system for detecting medicine packaging, extracting expiry dates using OCR, determining medicine validity, and providing illness information and safe disposal guidance.

---

## 📌 Table of Contents

* [About the Project](#-about-the-project)
* [Problem Statement](#-problem-statement)
* [Objectives](#-objectives)
* [Key Features](#-key-features)
* [System Architecture](#-system-architecture)
* [Project Workflow](#-project-workflow)
* [Technology Stack](#-technology-stack)
* [Dataset](#-dataset)
* [Annotation](#-annotation)
* [Project Structure](#-project-structure)
* [Installation](#-installation)
* [Django Setup](#-django-setup)
* [Environment Variables](#-environment-variables)
* [YOLOv8 Model](#-yolov8-model)
* [OCR Pipeline](#-ocr-pipeline)
* [AI Agents](#-ai-agents)
* [Database](#-database)
* [Testing](#-testing)
* [Security](#-security)
* [Project Team](#-project-team)
* [Project Status](#-project-status)
* [Future Improvements](#-future-improvements)
* [License](#-license)

---

# 📖 About the Project

The **Vision-Based Smart Medicine Waste Identifier** is a computer-vision project designed to assist in identifying potentially expired medicines and providing actionable information about their disposal.

The system processes an uploaded or captured medicine image using a modular pipeline consisting of:

```text
Image
  ↓
YOLOv8 Object Detection
  ↓
Expiry-Date Region Detection
  ↓
Image Preprocessing
  ↓
OCR
  ↓
Date Parsing
  ↓
Expiry Classification
  ↓
AI Agents
  ↓
Django Dashboard
```

The project combines **object detection, optical character recognition, date processing, and AI-agent-based web search** to move beyond simple image classification and provide useful information to the user.

---

# ❗ Problem Statement

Improper disposal of expired medicines can contribute to environmental contamination and create public-health concerns.

Identifying expired medicines manually can be inconvenient because:

* Expiry information may be printed in small text.
* Packaging can have different layouts.
* Expiry dates can appear at different positions.
* Images may contain angled or low-quality text.
* Users may not know the appropriate disposal method.

This project aims to automate the identification and evaluation process using computer vision, OCR, and AI-assisted information retrieval.

---

# 🎯 Objectives

The primary objectives are:

1. Detect medicine packaging from an uploaded or captured image.
2. Locate the printed expiry-date region.
3. Extract the expiry date using OCR.
4. Parse the detected date.
5. Determine whether the medicine is:

   * Valid
   * Expired
   * Needs Manual Review
6. Look up the common medical conditions associated with the detected medicine.
7. Provide appropriate disposal guidance for expired medicines.
8. Provide a Django-based web interface.
9. Maintain an administrative review queue for low-confidence cases.

---

# ✨ Key Features

## 🔍 Medicine Detection

Uses a custom-trained **YOLOv8n** model to detect medicine packaging.

## 📅 Expiry-Date Detection

Detects the printed expiry-date region separately from the medicine package.

## 🖼️ Image Preprocessing

The expiry-date crop can be processed using:

* Deskewing
* Contrast enhancement
* CLAHE
* Upscaling
* Noise reduction

## 🔤 OCR

The project uses:

* **EasyOCR** as the primary OCR engine
* **Tesseract** as a fallback OCR engine

## 📆 Date Parsing

The extracted OCR text is processed using:

* Python regular expressions
* `python-dateutil`

## ✅ Expiry Classification

The system classifies the medicine as:

```text
VALID
EXPIRED
NEEDS REVIEW
```

## 🤖 Illness Lookup Agent

An AI agent retrieves information about the medical conditions that the detected medicine commonly treats.

## ♻️ Disposal Guidance Agent

For expired medicines, an AI agent retrieves appropriate disposal guidance.

Possible guidance includes:

* Pharmacy take-back programs
* Household hazardous-waste programs
* Applicable do-not-flush guidance

## 🌐 Django Web Application

The Django application provides:

* Image upload
* Detection results
* OCR results
* Expiry status
* Medicine information
* Disposal information
* Scan history
* Review queue

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │    Image Input      │
                         │ Upload / Capture    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      YOLOv8n        │
                         │  Object Detection   │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
          ┌──────────────────┐           ┌──────────────────┐
          │ Medicine Package │           │ Expiry Date      │
          │    Detection     │           │    Detection     │
          └──────────────────┘           └────────┬─────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │ Image Preprocessing │
                                       │ OpenCV              │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │        OCR          │
                                       │ EasyOCR / Tesseract │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │    Date Parsing     │
                                       │ Regex + dateutil    │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │ Expiry Classification│
                                       └──────────┬──────────┘
                                                  │
                             ┌────────────────────┼────────────────────┐
                             │                    │                    │
                             ▼                    ▼                    ▼
                          VALID                EXPIRED              REVIEW
                                                  │
                                      ┌───────────┴───────────┐
                                      │                       │
                                      ▼                       ▼
                              ┌───────────────┐       ┌─────────────────┐
                              │ Illness Agent │       │ Disposal Agent  │
                              └───────┬───────┘       └────────┬────────┘
                                      │                        │
                                      └───────────┬────────────┘
                                                  ▼
                                       ┌─────────────────────┐
                                       │   Django Backend    │
                                       │ Views / Forms/Admin │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │  Results Dashboard  │
                                       │ History / Review    │
                                       └─────────────────────┘
```

The architecture follows the modular pipeline specified in the project implementation blueprint.

---

# 🔄 Project Workflow

## Step 1 — Image Input

The user uploads or captures an image of a medicine package.

## Step 2 — Object Detection

YOLOv8n detects:

```text
Medicine Package
Expiry Date Region
```

## Step 3 — Crop Extraction

The detected expiry-date region is cropped from the original image.

## Step 4 — Image Preprocessing

OpenCV improves the expiry-date crop.

## Step 5 — OCR

EasyOCR attempts to extract the printed expiry information.

Tesseract can be used as a fallback.

## Step 6 — Date Parsing

The OCR output is converted into a structured date.

## Step 7 — Expiry Evaluation

The extracted expiry date is compared against the current date.

## Step 8 — Classification

The result becomes:

```text
Valid
Expired
Needs Review
```

## Step 9 — Medicine Information

The illness lookup agent retrieves information about the detected medicine.

## Step 10 — Disposal Guidance

If the medicine is expired, the disposal guidance agent retrieves appropriate disposal information.

## Step 11 — Dashboard

The Django application displays the final results.

---

# 🛠️ Technology Stack

| Component             | Technology                       |
| --------------------- | -------------------------------- |
| Programming Language  | Python 3.11                      |
| Backend               | Django 5.1.x                     |
| Object Detection      | YOLOv8n / Ultralytics            |
| Computer Vision       | OpenCV                           |
| OCR                   | EasyOCR                          |
| OCR Fallback          | Tesseract                        |
| Deep Learning         | PyTorch                          |
| Image Processing      | Pillow                           |
| Numerical Processing  | NumPy                            |
| Date Parsing          | Python Regex + `python-dateutil` |
| AI Agents             | OpenAI Agents SDK                |
| Structured Output     | Pydantic                         |
| Background Processing | Celery                           |
| Message Broker        | Redis                            |
| Development Database  | SQLite                           |
| Production Database   | PostgreSQL                       |
| Annotation            | Roboflow                         |
| Containerization      | Docker                           |
| Deployment            | Render / Railway                 |
| Production Server     | Gunicorn                         |

The technology choices are based on the implementation blueprint supplied for the project.

---

# 📊 Dataset

## Current Dataset

The project currently contains:

```text
150 medicine images
```

The project brief specifies a target range of approximately **150–300 labeled images**, so the current 150-image dataset satisfies the lower end of the planned dataset scope.

## Recommended Split

| Dataset    | Percentage |  Images |
| ---------- | ---------: | ------: |
| Training   |        70% |     105 |
| Validation |        20% |      30 |
| Testing    |        10% |      15 |
| **Total**  |   **100%** | **150** |

## Dataset Diversity

The dataset should contain variations in:

* Medicine packaging
* Viewing angles
* Lighting conditions
* Backgrounds
* Image quality
* Expiry-date appearance

---

# 🏷️ Annotation

Annotation is performed using **Roboflow**.

## Annotation Classes

The YOLO dataset contains two classes:

```text
0 → medicine
1 → expiry_date
```

### `medicine`

Bounding box around the complete medicine package.

### `expiry_date`

Bounding box around the printed expiry-date region.

---

# 📁 Project Structure

```text
Medicine-Waste-Identifier/
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── waste_identifier/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── dataset/
│   ├── raw_images/
│   ├── train/
│   │   ├── images/
│   │   └── labels/
│   ├── valid/
│   │   ├── images/
│   │   └── labels/
│   └── test/
│       ├── images/
│       └── labels/
│
├── models/
│   └── best.pt
│
├── media/
│
├── static/
│
├── staticfiles/
│
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

# 🚀 Installation

## Prerequisites

Install:

* Python 3.11
* Git
* VS Code (recommended)
* Roboflow account
* Docker (required later for deployment)
* Tesseract OCR (required when using Tesseract fallback)

---

## 1. Clone Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Enter the project:

```bash
cd Medicine-Waste-Identifier
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

---

## 3. Activate Virtual Environment

### Windows CMD

```bash
venv\Scripts\activate
```

### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## 5. Install Project Dependencies

```bash
pip install -r requirements.txt
```

---

# ⚙️ Django Setup

## 1. Run Migrations

```bash
python manage.py migrate
```

## 2. Create Superuser

```bash
python manage.py createsuperuser
```

## 3. Run Development Server

```bash
python manage.py runserver
```

Application:

```text
http://127.0.0.1:8000/
```

Admin:

```text
http://127.0.0.1:8000/admin/
```

---

# 🔐 Environment Variables

Sensitive configuration should be stored in a `.env` file.

Example:

```env
DEBUG=False

SECRET_KEY=your-django-secret-key

ALLOWED_HOSTS=localhost,127.0.0.1

OPENAI_API_KEY=your-openai-api-key

OCR_ENGINE=easyocr

YOLO_WEIGHTS_PATH=models/best.pt

CACHE_TTL_SECONDS=2592000
```

For production, database and Redis configuration can also be provided through environment variables.

**Never commit `.env` to GitHub.**

---

# 🤖 YOLOv8 Model

The project uses **YOLOv8n** for object detection.

The model is trained to detect:

```text
medicine
expiry_date
```

After training, the best model is expected to be saved as:

```text
models/best.pt
```

Large model files should not be committed directly to Git.

---

# 🔤 OCR Pipeline

The OCR pipeline follows:

```text
YOLOv8
   ↓
Expiry Date Crop
   ↓
Deskew
   ↓
CLAHE
   ↓
Upscale
   ↓
EasyOCR
   ↓
Tesseract Fallback
   ↓
Date Parser
```

The implementation blueprint specifically proposes OpenCV preprocessing, EasyOCR as the primary engine, Tesseract as fallback, and `python-dateutil` for date parsing.

---

# 🤖 AI Agents

## Illness Lookup Agent

The Illness Lookup Agent receives the detected medicine name and searches for information about the medical conditions commonly treated by that medicine.

Technology:

```text
OpenAI Agents SDK
+
Web Search
```

---

## Disposal Guidance Agent

The Disposal Guidance Agent is triggered for expired medicines.

It searches for appropriate disposal guidance.

Potential sources and methods include:

* Pharmacy take-back programs
* Household hazardous-waste programs
* Applicable official flush-list guidance

Agent outputs should be structured and source-verified.

---

# 🗄️ Database

The initial development database is:

```text
SQLite
```

PostgreSQL is recommended for production.

The planned scan result data includes:

```text
image
medicine_name
detection_confidence
ocr_raw_text
expiry_date
status
illness_info
disposal_info
created_at
```

---

# ⚡ Background Processing

The project blueprint uses:

```text
Celery
+
Redis
```

for asynchronous tasks.

AI-agent lookups can be executed as background tasks rather than blocking the main upload request.

Caching can be used to avoid repeating the same medicine lookup unnecessarily.

---

# 🧪 Testing

Testing should be performed at multiple levels.

## Model Testing

Evaluate:

* Precision
* Recall
* mAP

## OCR Testing

Evaluate:

* Correct text extraction
* Date recognition
* Different image conditions

## Date Parser Testing

Test:

```text
MM/YYYY
DD/MM/YYYY
MMM YYYY
YYYY-MM
```

and other formats encountered in the dataset.

## End-to-End Testing

Test:

```text
Image
 ↓
Detection
 ↓
Crop
 ↓
Preprocessing
 ↓
OCR
 ↓
Date Parsing
 ↓
Expiry Classification
 ↓
Agent Lookup
 ↓
Dashboard
```

The project blueprint recommends validating individual stages independently before relying on the complete chained pipeline.

---

# 🐳 Docker Deployment

The planned deployment architecture contains:

```text
┌──────────────┐
│    Django    │
└──────┬───────┘
       │
       ├───────────────┐
       ▼               ▼
   PostgreSQL        Redis
                       │
                       ▼
                    Celery
```

Docker Compose can be used to run:

```text
web
worker
redis
db
```

The implementation blueprint specifies these four services for local deployment parity.

---

# ☁️ Cloud Deployment

Potential deployment platforms:

* Render
* Railway

Deployment should include:

* Django web service
* Celery worker
* PostgreSQL
* Redis
* Persistent media storage
* Model-weight storage

---

# 🔒 Security

The following must **never** be committed to the repository:

```text
.env
API Keys
Passwords
Database Credentials
Private User Data
Private Dataset
Large Model Weights
```

Recommended production protections include:

* `DEBUG=False`
* HTTPS
* Upload-size limits
* Rate limiting
* Environment-based secrets
* Celery task timeouts
* Logging and monitoring

The project blueprint recommends limiting uploaded images to 10 MB and protecting the upload endpoint against abuse.

---

# ⚠️ Limitations

The project may face challenges including:

### OCR Failure

Expiry text can be:

* Faded
* Angled
* Small
* Low contrast

### Limited Dataset

The current dataset contains 150 images, which is at the lower end of the project's planned 150–300 labeled-image range.

### Model Generalization

Performance may decrease on medicine packaging significantly different from the training dataset.

### AI Agent Reliability

Web-based AI-agent results require source verification and appropriate disclaimers.

### Processing Time

AI-agent web searches may introduce additional latency.

These risks and corresponding mitigations are identified in the project brief.

---

# 🔮 Future Improvements

Possible future improvements include:

* Larger medicine dataset
* More medicine-package categories
* Improved OCR
* Better expiry-date detection
* Medicine database/API integration
* Disposal-category classification
* CNN/transfer-learning-based disposal classification
* Mobile application
* Barcode/QR-code recognition
* Offline processing
* Improved review workflow
* Cloud-based monitoring

The disposal-category classifier is identified as a stretch goal in the current project brief.

---

# 👥 Project Team

| Name               | Role        |
| ------------------ | ----------- |
| Justin Earnest     | Team Member |
| Naveen M Vinod     | Team Member |
| Sherin A S         | Team Member |
| Susreedh Kumar S S | Team Member |

---

# 📊 Project Status

```text
Current Phase:
Phase 3 — Data Annotation
```

### Progress

```text
Phase 1  ████████████████████ 100%  ✅
Phase 2  ████████████████████ 100%  ✅
Phase 3  ██████████░░░░░░░░░░  50%  🔄
Phase 4  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 5  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 6  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 7  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 8  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 9  ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
Phase 10 ░░░░░░░░░░░░░░░░░░░░   0%  ⏳
```

---

# 📚 Project References

The project is based on the supplied project brief and implementation blueprint covering:

* Computer vision
* YOLOv8
* OCR
* Expiry-date detection
* Django
* OpenAI Agents SDK
* Web search
* Celery
* Redis
* PostgreSQL
* Docker
* Deployment

---

# 📄 License

This project is developed for **academic and educational purposes**.

---

# ⭐ Acknowledgements

This project uses open-source technologies and tools including:

* Django
* Ultralytics YOLO
* OpenCV
* EasyOCR
* PyTorch
* Roboflow
* Celery
* Redis

---

## 🚀 Project Goal

> **Detect → Read → Evaluate → Explain → Guide**

The ultimate goal is to create a practical computer-vision system that can help users identify potentially expired medicines and obtain appropriate information for safer disposal.
