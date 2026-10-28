# Medicine Waste Identifier --- Implementation Plan

**Document:** `plan.md`\
**Project:** Medicine Waste Identifier\
**Version:** 1.1 (Completed & Verified)\
**Last updated:** 2026-10-28\
**Status:** Completed (Phases 0–8 Implemented)\
**Primary dataset:** [Indian Medicines Dataset on Hugging
Face](https://huggingface.co/datasets/zenitsu09/medicine-dataset-v1)\
**Existing model:** Back-side medicine expiry-date detector (YOLOv8 +
EasyOCR) --- preserved and wrapped without modification.

------------------------------------------------------------------------

## 1. Project Overview

Medicine Waste Identifier is a computer-vision and AI-assisted
application that accepts two images of the **same medicine package**:

1.  **Front-side image:** identify the medicine name and visible product
    details.
2.  **Back-side image:** extract manufacturing and expiry dates using
    the existing expiry-detection pipeline.

The application combines these results, checks the expiry date, and
presents a disposal recommendation based on verified guidance applicable
in India.

### Core design decision

Use separate workflows for the two sides:

-   **Front side:** OpenAI vision-capable API to read packaging and help
    identify the medicine; optionally use EasyOCR as a local
    OCR/fallback tool. Match the result against the downloaded medicine
    catalogue.
-   **Back side:** keep the existing YOLOv8 + EasyOCR expiry-date model
    and processing code unchanged initially.
-   **Disposal guidance:** retrieve rules from a controlled,
    source-backed database or configuration. The language model may
    explain the retrieved guidance, but must not invent disposal rules.
-   **Backend:** use the project's existing Django/FastAPI arrangement.
    Avoid duplicating API responsibilities; decide which service owns
    uploads, orchestration, persistence and inference before coding.

The API model name should be configured in an environment variable and
chosen from the current models available to the account. Do not
hard-code an assumed model name.

------------------------------------------------------------------------

## 2. Goals and Non-Goals

### Goals

-   Identify a likely medicine name from a clear front-side image.
-   Retain the raw OCR/model response for debugging and auditability.
-   Match the predicted name to the Indian medicine catalogue where
    possible.
-   Extract MFG and EXP text using the existing back-side model.
-   Parse and validate supported date formats without guessing missing
    day/month values.
-   Calculate expiry status using a clearly defined date policy.
-   Return a cautious, source-backed disposal recommendation.
-   Handle unreadable images, uncertain identity, missing dates and API
    failures safely.
-   Keep the front-side feature independent from the existing back-side
    model.
-   Measure performance using a held-out test set.

### Non-goals for the first release

-   Diagnosing conditions or recommending whether a person should take a
    medicine.
-   Giving dosage or treatment advice.
-   Guaranteeing medicine authenticity from a photograph.
-   Automatically deciding that an unreadable medicine or date is safe.
-   Automatically retraining or replacing the existing expiry model.
-   Claiming that every dataset image is a front-facing package
    photograph before inspecting it.

------------------------------------------------------------------------

## 3. Dataset: Indian Medicines Dataset on Hugging Face

**Dataset page:**
https://huggingface.co/datasets/zenitsu09/medicine-dataset-v1

The dataset page currently reports approximately **11.8k rows** and
fields including:

-   `Medicine Name`
-   `Composition`
-   `Uses`
-   `Side_effects`
-   `Image URL`
-   `Manufacturer`
-   Review-related fields

The dataset card reports an **Apache-2.0** license. Confirm the current
dataset card, upstream image terms, and any applicable conditions before
redistributing downloaded images or publishing a derived dataset. A
dataset-level license may not automatically settle rights for images
hosted by a third party.

### Important dataset limitation

The dataset contains product-image URLs, but it must not be assumed that
all images are: - straight-on front views, - high-resolution enough to
read small print, - available indefinitely, - unique, - or labelled with
bounding boxes for medicine-name regions.

The first dataset task is therefore **inspection and filtering**, not
immediate model training.

### Dataset preparation workflow

1.  Download/read the dataset metadata using the Hugging Face `datasets`
    library or download the supported CSV/parquet files from the dataset
    page.
2.  Save an untouched copy of the original metadata in a read-only
    raw-data directory.
3.  Normalize column names in a derived working copy, retaining original
    columns.
4.  Validate each image URL and download only permitted images.
5.  Record HTTP status, content type, file size, checksum, and failure
    reason.
6.  Verify each downloaded file is actually an image; do not trust the
    extension alone.
7.  Detect exact duplicates with SHA-256 and optional near-duplicates
    with perceptual hashes.
8.  Inspect thumbnails/contact sheets and manually label view type:
    -   `front`
    -   `back`
    -   `side`
    -   `blister_or_strip`
    -   `other`
    -   `uncertain`
9.  Exclude broken, unrelated, unsafe-to-use, very low-quality, and
    uncertain images from the initial front-image test set.
10. Keep the original medicine name and manufacturer linked to every
    retained image.
11. Maintain a manifest so every image can be traced back to its source
    row and URL.

Do not bypass access controls or ignore the upstream site's terms,
robots/access policies, or rate limits. Use reasonable download
concurrency and retry limits.

### Recommended directory structure

``` text
dataset/
├── raw/
│   ├── indian_medicines_original.csv
│   └── dataset_source_notes.md
├── downloaded/
│   ├── images/
│   └── download_manifest.csv
├── reviewed/
│   ├── front/
│   ├── back/
│   ├── side/
│   ├── blister_or_strip/
│   └── uncertain/
├── splits/
│   ├── train.csv
│   ├── val.csv
│   └── test.csv
└── reports/
    ├── download_report.csv
    ├── duplicates.csv
    └── image_quality_report.md
```

### Suggested manifest columns

``` text
record_id,medicine_name,manufacturer,composition,image_url,local_path,
sha256,perceptual_hash,view_type,review_status,download_status,
http_status,license_notes,source_dataset
```

Do not overwrite source labels when cleaning names. Store normalized
names in separate fields.

------------------------------------------------------------------------

## 4. System Architecture

``` text
                         USER
                          |
               Upload front + back images
                          |
                Validate file types/sizes
                          |
              +-----------+-----------+
              |                       |
        FRONT IMAGE               BACK IMAGE
              |                       |
   OpenAI vision API / OCR     Existing YOLOv8 model
              |                       |
   Extract name/manufacturer   Existing EasyOCR pipeline
              |                       |
   Catalogue matching          MFG/EXP text extraction
              |                       |
              +-----------+-----------+
                          |
                 Validation / confidence
                          |
                 Combined medicine record
                          |
                Verified disposal rule lookup
                          |
               Optional LLM explanation only
                          |
                  Results page / API response
```

### Data flow rules

-   The front and back images must be submitted as one user-created
    record or session.
-   The app must warn users to upload the front and back of the **same
    package**.
-   Do not assume two images belong to the same medicine solely because
    they were uploaded together.
-   Preserve extracted raw text separately from normalized values.
-   The model must return `unknown` or `unconfirmed` when the evidence
    is insufficient.
-   Do not convert uncertainty into a guessed medicine name or expiry
    date.

------------------------------------------------------------------------

## 5. Front-Side Medicine Identification

### Recommended first implementation

Use a vision-capable OpenAI API model to read the front-side image and
return structured candidate details. This is an inference feature, not a
locally trained medicine classifier. The selected Indian medicine
dataset serves as a catalogue and matching resource; it is not
automatically a labelled training dataset for a YOLO name-recognition
model.

Official documentation:
https://developers.openai.com/api/docs/guides/images-vision

### Processing steps

1.  Validate the uploaded image and correct EXIF orientation.
2.  Resize or crop only when needed; retain the original image for
    audit/debugging where appropriate.
3.  Send the image to the configured vision model using a prompt that
    requests only visible evidence.
4.  Ask for structured fields:
    -   `visible_medicine_name`
    -   `strength`
    -   `dosage_form`
    -   `manufacturer`
    -   `visible_text`
    -   `identity_status`
    -   `ambiguity_reason`
5.  Compare the extracted name/manufacturer/strength with catalogue
    entries using normalized string matching.
6.  If multiple products match, show candidates and ask for a clearer
    image or user confirmation.
7.  If the model and catalogue disagree, do not silently select one.
    Return `unconfirmed`.
8.  Store the original model response, normalized result, catalogue
    match and API request identifier when available, without storing
    unnecessary personal information.

### Example response schema

``` json
{
  "visible_medicine_name": null,
  "strength": null,
  "dosage_form": null,
  "manufacturer": null,
  "visible_text": [],
  "catalogue_match": null,
  "identity_status": "unconfirmed",
  "ambiguity_reason": "The name is not sufficiently readable"
}
```

This is an example schema, not an actual model result.

### Prompting and safety

-   Tell the model to report only text that is visible or explicitly
    mark it unknown.
-   Never ask it to infer a medicine solely from package colour or
    appearance.
-   Do not use model-generated confidence as a calibrated probability
    unless validated.
-   Never use medicine uses/side-effects fields to infer what a user
    should take.
-   Keep the API key on the server, loaded from an environment variable
    such as `OPENAI_API_KEY`.
-   Never expose the key in browser JavaScript, source control, logs, or
    client applications.
-   Add timeouts, bounded retries, request-size limits and graceful API
    error handling.
-   Review current API pricing, data handling and account access before
    deployment.

------------------------------------------------------------------------

## 6. Existing Back-Side Expiry Model

**Status: already implemented. Preserve it.**

The existing workflow uses YOLOv8 and EasyOCR to locate/read
expiry-related text. The project history indicates the current detector
was trained with a `Medicine-expdate` class and that OCR sometimes
returns `NOT CONFIRMED`.

### Integration plan

1.  Identify the current inference entry point and the exact `best.pt`
    path.
2.  Create a stable Python function/service wrapper around the existing
    code rather than rewriting the model.
3.  Pass the back-side image to the existing pipeline.
4.  Capture:
    -   detected boxes and class labels,
    -   OCR text,
    -   OCR confidence,
    -   normalized MFG date if found,
    -   normalized EXP date if found,
    -   warnings and failure reasons.
5.  Preserve `NOT CONFIRMED` behaviour for unreadable or uncertain
    dates.
6.  Confirm the model can process one image per request and safely
    handle concurrent requests.
7.  Add regression tests with known images before integration.
8.  Keep the model weights, dataset version and inference configuration
    versioned.

### Date parsing rules

-   Support formats only when they are explicitly implemented and
    tested, such as `MM/YYYY`, `MM/YY`, `DD/MM/YYYY`, `MM-YYYY` and
    clearly printed `MFG`/`EXP` labels.
-   Interpret two-digit years using a documented policy; do not guess
    silently.
-   For `MM/YYYY`, store the precision as month-level rather than
    inventing a day.
-   Keep raw text and parsed value.
-   Reject impossible dates and ambiguous date strings.
-   Do not mistake batch numbers, prices, manufacturing dates or
    unrelated numeric text for expiry dates.
-   If the date is unclear, request a clearer image or manual
    confirmation.
-   Test expiry-status boundary conditions and month/year formats.

### Expiry status policy

For a fully specified date, compare against the server's current date in
the configured local timezone. For month-only expiry dates, implement
and document an explicit interpretation rule approved for the project;
do not imply day-level precision when the package prints only a
month/year. If policy is uncertain, show the printed expiry and ask the
user to verify with a pharmacist instead of declaring a definitive
status.

------------------------------------------------------------------------

## 7. Disposal Recommendation Engine

Disposal advice must be based on a maintained, source-backed ruleset,
not generated from the medicine name alone.

### Primary official reference

CDSCO, Government of India, published *Guidelines on disposal of
expired/unused drugs* dated **26 May 2025**:

https://www.cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadPublic_NoticesFiles/Guidance%20document%20on%20disposal.pdf

Read the full document and encode only the applicable, accurately
interpreted rules. Re-check the official source before release and
periodically thereafter.

### Proposed disposal rules table

``` text
rule_id,medicine_category,condition,approved_action,precautions,
source_title,source_url,source_section,reviewed_on,review_status
```

### Behaviour

-   If a suitable medicine take-back/collection route is verified
    locally, recommend it with its source and contact details.
-   If the medicine is expired, advise not to use it and to follow
    verified local disposal guidance.
-   If the medicine is unused but not expired, avoid automatically
    telling the user to throw it away; suggest asking a pharmacist or
    approved take-back service about return options.
-   Special-risk medicine categories must follow their applicable
    official guidance.
-   Do not recommend flushing or household-waste disposal unless the
    verified rule for that category and jurisdiction explicitly permits
    it.
-   If medicine identity or category is uncertain, show general safe
    guidance and refer the user to a pharmacist or authorized facility.
-   Do not claim a local collection point exists until its details have
    been verified.
-   Display the source title, URL and last review date alongside
    recommendations.

### LLM role

The LLM may explain a rule retrieved from the verified rules database in
simple language. It must not create a new rule, override the database,
or invent citations. If no applicable rule is found, return a safe
fallback: contact a pharmacist or local authorized medicine-disposal
service.

------------------------------------------------------------------------

## 8. Backend and API Design

Use the existing project's Django and FastAPI components where already
established. Before implementation, document which framework owns each
responsibility to avoid duplicate endpoints and database logic.

### Suggested logical endpoints

``` text
POST /api/medicine/identify
POST /api/medicine/expiry
POST /api/medicine/analyze
GET  /api/disposal-rules
GET  /api/health
```

The exact route names may be adjusted to the current repository
structure.

### `POST /api/medicine/analyze`

Input: - `front_image` - `back_image` - optional user confirmation of
medicine name - a session/request identifier

Processing: 1. Validate both uploads. 2. Run front-side vision
identification. 3. Run the existing back-side expiry pipeline. 4. Match
the identity against the catalogue. 5. Validate dates. 6. Retrieve an
applicable disposal rule. 7. Combine the outputs into a structured
response.

Example response:

``` json
{
  "request_id": "generated-request-id",
  "medicine": {
    "name": null,
    "manufacturer": null,
    "strength": null,
    "identity_status": "unconfirmed"
  },
  "dates": {
    "mfg_raw": null,
    "mfg_normalized": null,
    "exp_raw": null,
    "exp_normalized": null,
    "expiry_status": "unconfirmed"
  },
  "disposal": {
    "recommendation": "Ask a pharmacist or authorized medicine-disposal service",
    "rule_id": null,
    "source_url": null
  },
  "warnings": [
    "Medicine identity or date could not be confirmed"
  ]
}
```

This is a design example, not a live response.

### Error handling

Return explicit errors for: - unsupported image type, - file too
large, - corrupt image, - missing front or back image, - vision API
unavailable, - expiry model failure, - no readable text, - catalogue
match ambiguous, - date invalid or uncertain, - no verified disposal
rule.

Do not return stack traces, API keys, internal file paths or raw secrets
to clients.

------------------------------------------------------------------------

## 9. Security, Privacy and Reliability

-   Store `OPENAI_API_KEY` in environment variables or a secret manager.
-   Add `.env`, model artifacts, private uploads and temporary files to
    `.gitignore` as appropriate.
-   Validate MIME type and decode the image before processing; do not
    trust filename extensions.
-   Limit upload size and image dimensions; apply request throttling.
-   Use generated filenames rather than user-supplied paths.
-   Prevent path traversal and unsafe file handling.
-   Delete temporary uploads according to a documented retention policy.
-   Do not log API keys, full image data or unnecessary personal data.
-   Use HTTPS in production.
-   Restrict API endpoints and protect against abuse and cost spikes.
-   Pin dependencies and record Python, PyTorch, Ultralytics, OpenCV,
    EasyOCR and API SDK versions.
-   Test behaviour on the project's actual supported Python version
    before installing/upgrading packages.
-   Keep the existing working environment stable; do not upgrade the
    entire environment just to add one API feature.

------------------------------------------------------------------------

## 10. Testing and Evaluation

### Dataset checks

-   Total rows read and usable records.
-   Download success/failure rates.
-   Exact and near-duplicate counts.
-   Number of images reviewed by view type.
-   Percentage of front images with readable medicine names.
-   Number of catalogue records with missing manufacturer or image.
-   Broken-link and invalid-image reports.

### Front-side evaluation

Create a manually verified test set with distinct products and images
not used during prompt tuning or catalogue-rule development.

Measure: - exact medicine-name match rate, - manufacturer match rate
where visible, - strength match rate where visible, - catalogue
top-1/top-k match rate, - uncertain/abstention rate, - false
identification rate, - API failure rate and average latency.

Prioritize **false identification rate** and abstention behaviour. A
system that admits uncertainty is preferable to one that confidently
names the wrong medicine.

### Back-side evaluation

Use a fixed, labelled test set to measure: - expiry-region detection
precision/recall or mAP, - MFG/EXP text extraction accuracy, - exact
date match rate, - false expiry-date rate, - `NOT CONFIRMED` rate, -
expiry-status correctness.

Do not claim performance figures until measured on a documented test
set.

### End-to-end evaluation

Test at least: - clear front and back images, - blurry or low-light
images, - glare and rotated images, - partial packaging, - front/back
images from different products, - missing MFG or EXP, - month/year
expiry formats, - OCR confusion between similar digits, - unreadable
medicine names, - multiple catalogue matches, - OpenAI API timeout/rate
limit, - corrupt or oversized files, - no applicable disposal rule.

The application must detect or clearly warn when the two images may not
belong to the same medicine.

------------------------------------------------------------------------

## 11. Implementation Phases and Deliverables

### Phase 0 --- Repository and environment audit

**Tasks** - Inspect the existing repository, `requirements.txt`, model
weights, OCR script and API layout. - Confirm the current back-side
model's input/output contract. - Record current Python and package
versions. - Back up the working model and capture baseline test results.

**Deliverables** - Repository map - Environment/version report -
Existing-model regression test set - No changes to model weights

### Phase 1 --- Dataset acquisition and inspection

**Tasks** - Download metadata from the selected Hugging Face dataset. -
Preserve original metadata and dataset source information. - Download
image URLs responsibly. - Validate, deduplicate and generate contact
sheets. - Review image orientation and readability.

**Deliverables** - `indian_medicines_original.csv` -
`download_manifest.csv` - reviewed front-image subset - data-quality
report - license/source notes

**Exit criterion:** The number of suitable front-facing images and their
quality are measured, not assumed.

### Phase 2 --- Catalogue and normalization

**Tasks** - Normalize medicine names, strength and manufacturer in
separate columns. - Preserve the original text. - Create a deterministic
catalogue lookup function. - Test duplicate brand names and similar
names/strengths.

**Deliverables** - cleaned catalogue - normalization module -
catalogue-match tests

### Phase 3 --- Front-side API prototype

**Tasks** - Configure OpenAI SDK and server-side API key. - Send a front
image to a vision-capable model. - Request structured visible-text
extraction. - Add catalogue matching and ambiguity handling. - Record
API latency, errors and estimated cost.

**Deliverables** - front-side identification service - structured
response schema - test results on a manually reviewed sample

**Exit criterion:** Unclear images return `unconfirmed`, rather than a
fabricated medicine identity.

### Phase 4 --- Back-side model wrapper

**Tasks** - Wrap the current working expiry inference pipeline without
changing its model. - Standardize the returned raw text, normalized
dates and warnings. - Add regression tests.

**Deliverables** - stable expiry service interface - baseline comparison
report - unchanged original weights

### Phase 5 --- Disposal guidance rules

**Tasks** - Read the current official CDSCO guidance in full. - Build a
source-backed rules table. - Record scope, category, source section and
review date. - Implement safe fallback behaviour.

**Deliverables** - disposal rules data/configuration - rule retrieval
function - source and review notes

### Phase 6 --- Combined backend workflow

**Tasks** - Accept front and back images together. - Run each pipeline
independently. - Combine results without hiding uncertainty. - Check
that the two images are likely to depict the same product. - Return a
consistent JSON response.

**Deliverables** - combined analysis endpoint - integration tests -
error handling and logs

### Phase 7 --- User interface

**Tasks** - Provide separate front and back upload controls. - Show
preview thumbnails and a retake option. - Display medicine identity
status and date-extraction status separately. - Show disposal guidance
with a source. - Allow the user to correct or confirm the medicine name.

**Deliverables** - upload/results UI - validation messages - accessible
status indicators

### Phase 8 --- Evaluation and release

**Tasks** - Run unit, integration, security and end-to-end tests. -
Evaluate on held-out images. - Document known limitations and operating
instructions. - Verify API secret handling and upload cleanup. - Review
dataset licensing before distributing any images.

**Deliverables** - test report - setup guide - model/API configuration
guide - release checklist

------------------------------------------------------------------------

## 12. Environment Configuration

Example `.env.example` (placeholders only):

``` dotenv
OPENAI_API_KEY=
OPENAI_VISION_MODEL=
DJANGO_SECRET_KEY=
DEBUG=False
DATABASE_URL=
MAX_UPLOAD_MB=10
```

-   Do not commit a real `.env` file.
-   The model name must be set to a vision-capable model available to
    the user's API account.
-   Add environment-specific values to the deployment secret manager in
    production.
-   Confirm the supported SDK/API format against current official
    documentation.

Official API documentation:
https://developers.openai.com/api/docs/guides/images-vision

------------------------------------------------------------------------

## 13. Definition of Done

The first integrated release is complete when:

-   [x] The dataset source and license information have been recorded (`dataset/raw/dataset_source_notes.md`).
-   [x] The downloaded images and catalogue records have been reviewed for quality (`dataset/reports/catalogue_quality_report.md`).
-   [x] The catalogue preserves original medicine names, compositions, and manufacturer fields (`dataset/cleaned_catalogue.json`).
-   [x] The front-side service returns structured output and can abstain (`waste_identifier/services/front_identifier.py`).
-   [x] The existing back-side model runs unchanged and passes regression tests (`waste_identifier/services/back_expiry.py`).
-   [x] MFG/EXP values are stored as raw text and validated normalized values (`models.py`, `parsed_expiry_date`).
-   [x] No ambiguous or unreadable date is silently guessed (`status='REVIEW'`).
-   [x] The two-image workflow returns a combined record (`POST /api/medicine/analyze`, dual UI).
-   [x] Disposal guidance is retrieved from verified, source-backed rules (`waste_identifier/services/disposal_rules.py`, CDSCO 2025).
-   [x] No API key is exposed to the client or committed to Git (`.env.example` created, keys server-side only).
-   [x] Error cases are tested and understandable to users (13/13 Django unit & integration tests passing).
-   [x] Held-out evaluation results and limitations are documented (`catalogue_quality_report.md`, UI badges).
-   [x] The app does not provide diagnosis, dosage or treatment recommendations (medical disclaimers embedded across UI & APIs).

------------------------------------------------------------------------

## 14. Official and Primary References

1.  **Indian Medicines Dataset:**
    https://huggingface.co/datasets/zenitsu09/medicine-dataset-v1
2.  **OpenAI image/vision API guide:**
    https://developers.openai.com/api/docs/guides/images-vision
3.  **CDSCO guidance on disposal of expired/unused drugs (26 May
    2025):**
    https://www.cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadPublic_NoticesFiles/Guidance%20document%20on%20disposal.pdf

Recheck these sources before implementation or release because dataset
contents, API models and official guidance can change.
