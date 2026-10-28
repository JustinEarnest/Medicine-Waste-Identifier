import base64
import os
import random
import uuid
from pathlib import Path
from typing import Optional, Tuple
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import Count, Q
from django.contrib import messages

from .models import ScanRecord
from .services.front_identifier import identify_front_medicine
from .services.back_expiry import analyze_back_expiry
from .services.disposal_rules import get_disposal_rule, get_all_disposal_rules, classify_category
from .services.catalogue import match_catalogue, load_catalogue


def home_view(request):
    """Landing page featuring live dual scanner upload, quick stats, and recent scans."""
    scans = ScanRecord.objects.all()
    total_count = scans.count()
    valid_count = scans.filter(status='VALID').count()
    expired_count = scans.filter(status='EXPIRED').count()
    review_count = scans.filter(status='REVIEW').count()

    recent_scans = scans[:6]

    context = {
        'total_count': total_count,
        'valid_count': valid_count,
        'expired_count': expired_count,
        'review_count': review_count,
        'recent_scans': recent_scans,
    }
    return render(request, 'waste_identifier/home.html', context)


def parse_image_upload(request, field_name: str, webcam_field: str) -> Tuple[Optional[ContentFile], Optional[str]]:
    """Helper to extract an image file from either multipart upload or base64 webcam payload."""
    uploaded_file = request.FILES.get(field_name)
    webcam_data = request.POST.get(webcam_field)

    if uploaded_file:
        return uploaded_file, uploaded_file.name

    if webcam_data and ';base64,' in webcam_data:
        format_part, img_str = webcam_data.split(';base64,')
        ext = format_part.split('/')[-1] if '/' in format_part else 'jpg'
        rand_id = uuid.uuid4().hex[:8]
        return ContentFile(base64.b64decode(img_str), name=f"{field_name}_{rand_id}.{ext}"), f"{field_name}_{rand_id}.{ext}"

    return None, None


@require_POST
def scan_upload_view(request):
    """
    Processes dual packaging uploads (Front + Back) or single image uploads.
    Orchestrates Front Identification and Back Expiry Detection (plan.md Phase 6).
    """
    front_file, front_name = parse_image_upload(request, 'front_image', 'front_webcam')
    back_file, back_name = parse_image_upload(request, 'back_image', 'back_webcam')

    # Fallback to single legacy 'image' field if neither explicit side given
    if not front_file and not back_file:
        single_file, single_name = parse_image_upload(request, 'image', 'webcam_data')
        if single_file:
            # When only 1 image provided, treat as back expiry primarily, with front fallback
            back_file, back_name = single_file, single_name
        else:
            messages.error(request, "Please provide at least one medicine package photo (Front or Back view).")
            return redirect('waste_identifier:home')

    # Create Initial ScanRecord
    scan = ScanRecord.objects.create(
        title=f"Scan: {Path(front_name or back_name or 'package').stem[:30]}",
        front_image=front_file,
        back_image=back_file,
        image=back_file or front_file,
    )

    output_dir = Path(settings.MEDIA_ROOT) / "processed" / str(scan.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = []

    # 1. Front-side Medicine Identification
    front_info = {}
    if scan.front_image:
        front_path = Path(scan.front_image.path)
        front_info = identify_front_medicine(front_path)

        scan.medicine_name = front_info.get("visible_medicine_name", "Unconfirmed Medicine")
        scan.manufacturer = front_info.get("manufacturer", "")
        scan.composition = front_info.get("composition", "")
        scan.dosage_form = front_info.get("dosage_form", "")
        scan.strength = front_info.get("strength", "")
        scan.identity_status = front_info.get("identity_status", "unconfirmed")
        scan.catalogue_confidence = front_info.get("catalogue_confidence", 0.0)
        scan.raw_front_text = " \n".join(front_info.get("visible_text", []))
        scan.illness_info = front_info.get("illness_uses", "")

        if front_info.get("ambiguity_reason"):
            warnings.append(f"Front Package: {front_info['ambiguity_reason']}")

    # 2. Back-side Expiry Detection
    back_info = {}
    if scan.back_image:
        back_path = Path(scan.back_image.path)
        back_info = analyze_back_expiry(back_path, output_dir=output_dir, file_stem=f"scan_{scan.id}")

        if back_info.get("success"):
            scan.annotated_image = f"processed/{scan.id}/{back_info['annotated_filename']}"
            scan.crop_image = f"processed/{scan.id}/{back_info['crop_filename']}"
            scan.raw_ocr_text = back_info.get("raw_ocr_text", "")
            scan.mfg_date = back_info.get("mfg_date_normalized", "") or ""
            scan.exp_date = back_info.get("exp_date_normalized", "") or ""
            scan.parsed_expiry_date = back_info.get("parsed_expiry_date")
            scan.status = back_info.get("expiry_status", "REVIEW")
            scan.confidence = back_info.get("confidence", 0.0)

            for w in back_info.get("warnings", []):
                warnings.append(f"Back Expiry: {w}")
        else:
            scan.status = 'REVIEW'
            warnings.append("Back expiry pipeline failed to locate date candidate.")

    # Discrepancy & Single-Side Checks
    if not scan.front_image and scan.back_image:
        warnings.append("Note: Front package image was not provided. Medicine identity derived from back label.")
        # If no front image, try to match medicine name from back OCR text
        if scan.raw_ocr_text:
            back_match = match_catalogue(scan.raw_ocr_text[:60])
            if back_match.get("match"):
                m = back_match["match"]
                scan.medicine_name = m.get("name", scan.medicine_name)
                scan.composition = m.get("composition", "")
                scan.manufacturer = m.get("manufacturer", "")
                scan.dosage_form = m.get("dosage_form", "")
                scan.illness_info = m.get("uses", "")
                scan.identity_status = back_match.get("status", "unconfirmed")
                scan.catalogue_confidence = back_match.get("confidence", 0.0)

    if scan.front_image and not scan.back_image:
        warnings.append("Note: Back package image was not provided. Expiry date cannot be validated.")
        scan.status = 'REVIEW'

    # Check for possible cross-package mismatch
    if scan.front_image and scan.back_image and scan.medicine_name != "Unconfirmed Medicine":
        back_ocr_upper = scan.raw_ocr_text.upper()
        norm_med = scan.medicine_name.upper().split()[0]
        if len(norm_med) >= 4 and norm_med not in back_ocr_upper and len(back_ocr_upper) > 20:
            warnings.append("Notice: Please verify that both photos depict the front and back of the exact same packaging.")

    # 3. Retrieve Verified CDSCO Disposal Rule
    disposal_rule = get_disposal_rule(
        status=scan.status,
        medicine_name=scan.medicine_name,
        composition=scan.composition,
        dosage_form=scan.dosage_form
    )

    scan.disposal_rule_id = disposal_rule.get("rule_id", "")
    scan.disposal_category = disposal_rule.get("medicine_category", "")
    scan.disposal_guidance = disposal_rule.get("approved_action", "")
    scan.disposal_precautions = disposal_rule.get("precautions", "")
    scan.disposal_source_url = disposal_rule.get("source_url", "")
    scan.disposal_source_section = disposal_rule.get("source_section", "")

    scan.warnings = "\n".join(warnings)
    scan.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
        return JsonResponse({
            'success': True,
            'redirect_url': f"/scan/{scan.id}/",
            'scan_id': scan.id,
            'status': scan.status,
            'medicine_name': scan.medicine_name,
            'identity_status': scan.identity_status,
        })

    return redirect('waste_identifier:scan_detail', pk=scan.pk)


@require_POST
def confirm_name_view(request, pk):
    """
    Allows user or operator to manually confirm or correct the detected medicine name.
    Re-matches with the Indian catalogue and updates verified disposal rules (plan.md Phase 7).
    """
    scan = get_object_or_404(ScanRecord, pk=pk)
    user_name = request.POST.get('medicine_name', '').strip()

    if user_name:
        match_result = match_catalogue(user_name)
        match_item = match_result.get("match")

        scan.medicine_name = user_name
        if match_item:
            scan.medicine_name = match_item.get("name", user_name)
            scan.manufacturer = match_item.get("manufacturer", scan.manufacturer)
            scan.composition = match_item.get("composition", scan.composition)
            scan.dosage_form = match_item.get("dosage_form", scan.dosage_form)
            scan.illness_info = match_item.get("uses", scan.illness_info)
            scan.identity_status = 'confirmed'
            scan.catalogue_confidence = 1.0
        else:
            scan.identity_status = 'ambiguous'

        # Refresh disposal rule with corrected name & composition
        rule = get_disposal_rule(
            status=scan.status,
            medicine_name=scan.medicine_name,
            composition=scan.composition,
            dosage_form=scan.dosage_form
        )
        scan.disposal_rule_id = rule.get("rule_id", "")
        scan.disposal_category = rule.get("medicine_category", "")
        scan.disposal_guidance = rule.get("approved_action", "")
        scan.disposal_precautions = rule.get("precautions", "")
        scan.disposal_source_url = rule.get("source_url", "")
        scan.disposal_source_section = rule.get("source_section", "")

        scan.save()
        messages.success(request, f"Updated and verified medicine identity: {scan.medicine_name}")

    return redirect('waste_identifier:scan_detail', pk=pk)


def sample_scan_view(request):
    """Runs a demonstration scan using one of the pre-configured test dataset images."""
    test_dir = settings.BASE_DIR / "dataset" / "roboflow_export" / "test" / "images"
    if not test_dir.is_dir():
        test_dir = settings.BASE_DIR / "dataset" / "test" / "images"

    sample_images = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))
    if not sample_images:
        messages.error(request, "No sample dataset images found.")
        return redirect('waste_identifier:home')

    selected_sample = random.choice(sample_images)

    with open(selected_sample, "rb") as f:
        content_file = ContentFile(f.read(), name=f"sample_{selected_sample.name}")

    scan = ScanRecord.objects.create(
        title=f"Sample: {selected_sample.stem[:24]}",
        back_image=content_file,
        image=content_file,
    )

    output_dir = Path(settings.MEDIA_ROOT) / "processed" / str(scan.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    back_info = analyze_back_expiry(Path(scan.back_image.path), output_dir=output_dir, file_stem=f"scan_{scan.id}")

    if back_info.get("success"):
        scan.annotated_image = f"processed/{scan.id}/{back_info['annotated_filename']}"
        scan.crop_image = f"processed/{scan.id}/{back_info['crop_filename']}"
        scan.raw_ocr_text = back_info.get("raw_ocr_text", "")
        scan.mfg_date = back_info.get("mfg_date_normalized", "") or ""
        scan.exp_date = back_info.get("exp_date_normalized", "") or ""
        scan.parsed_expiry_date = back_info.get("parsed_expiry_date")
        scan.status = back_info.get("expiry_status", "REVIEW")
        scan.confidence = back_info.get("confidence", 0.0)

        # Match name candidate from catalogue
        cat_match = match_catalogue(scan.raw_ocr_text[:50])
        if cat_match.get("match"):
            m = cat_match["match"]
            scan.medicine_name = m.get("name", "Medicine Package")
            scan.manufacturer = m.get("manufacturer", "")
            scan.composition = m.get("composition", "")
            scan.dosage_form = m.get("dosage_form", "")
            scan.illness_info = m.get("uses", "")
            scan.identity_status = cat_match.get("status", "unconfirmed")
            scan.catalogue_confidence = cat_match.get("confidence", 0.0)
        else:
            scan.medicine_name = "Sample Medicine Strip"
            scan.identity_status = "unconfirmed"

        disposal_rule = get_disposal_rule(
            status=scan.status,
            medicine_name=scan.medicine_name,
            composition=scan.composition,
            dosage_form=scan.dosage_form
        )
        scan.disposal_rule_id = disposal_rule.get("rule_id", "")
        scan.disposal_category = disposal_rule.get("medicine_category", "")
        scan.disposal_guidance = disposal_rule.get("approved_action", "")
        scan.disposal_precautions = disposal_rule.get("precautions", "")
        scan.disposal_source_url = disposal_rule.get("source_url", "")
        scan.disposal_source_section = disposal_rule.get("source_section", "")
        scan.save()

    messages.success(request, f"Loaded and analyzed test sample: {selected_sample.name}")
    return redirect('waste_identifier:scan_detail', pk=scan.pk)


def scan_detail_view(request, pk):
    """Detailed visual report of the front/back analysis, OCR, catalogue verification, and disposal advice."""
    scan = get_object_or_404(ScanRecord, pk=pk)
    
    # Retrieve top 5 catalogue candidates if ambiguous or for manual name confirmation dropdown
    candidates = []
    if scan.medicine_name:
        match_res = match_catalogue(scan.medicine_name, top_k=5)
        candidates = match_res.get("candidates", [])

    context = {
        'scan': scan,
        'candidates': candidates,
        'has_both_images': bool(scan.front_image and scan.back_image),
    }
    return render(request, 'waste_identifier/scan_detail.html', context)


@require_POST
def mark_reviewed_view(request, pk):
    """Allows an operator or user to confirm manual review of an ambiguous scan."""
    scan = get_object_or_404(ScanRecord, pk=pk)
    scan.is_reviewed = not scan.is_reviewed
    scan.save()
    messages.success(request, f"Scan #{scan.id} review status updated to: {'Verified' if scan.is_reviewed else 'Unverified'}.")
    return redirect('waste_identifier:scan_detail', pk=pk)


def history_view(request):
    """Archive of all scanned medicines with status filters and keyword search."""
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '')

    scans = ScanRecord.objects.all()

    if status_filter in ['VALID', 'EXPIRED', 'REVIEW']:
        scans = scans.filter(status=status_filter)

    if query:
        scans = scans.filter(
            Q(medicine_name__icontains=query) |
            Q(composition__icontains=query) |
            Q(raw_ocr_text__icontains=query) |
            Q(raw_front_text__icontains=query) |
            Q(exp_date__icontains=query)
        )

    context = {
        'scans': scans,
        'current_status': status_filter,
        'search_query': query,
        'total_count': ScanRecord.objects.count(),
        'valid_count': ScanRecord.objects.filter(status='VALID').count(),
        'expired_count': ScanRecord.objects.filter(status='EXPIRED').count(),
        'review_count': ScanRecord.objects.filter(status='REVIEW').count(),
    }
    return render(request, 'waste_identifier/history.html', context)


def disposal_guide_view(request):
    """Comprehensive guide on pharmaceutical waste management with verified CDSCO 2025 rules."""
    rules = get_all_disposal_rules()
    return render(request, 'waste_identifier/disposal_guide.html', {'rules': rules})


# --------------------------------------------------------------------------
# REST API Endpoints (plan.md Section 8)
# --------------------------------------------------------------------------

@csrf_exempt
def api_identify_view(request):
    """POST /api/medicine/identify: Front packaging identification & catalogue matching."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)

    img_file = request.FILES.get('front_image') or request.FILES.get('image')
    if not img_file:
        return JsonResponse({'error': 'Missing front_image in request form-data'}, status=400)

    # Save temporary file for inference
    temp_dir = Path(settings.MEDIA_ROOT) / "temp_api"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"front_{uuid.uuid4().hex[:8]}_{img_file.name}"

    with open(temp_path, "wb") as f:
        for chunk in img_file.chunks():
            f.write(chunk)

    try:
        result = identify_front_medicine(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return JsonResponse({
        "status": "success",
        "visible_medicine_name": result.get("visible_medicine_name"),
        "strength": result.get("strength"),
        "dosage_form": result.get("dosage_form"),
        "manufacturer": result.get("manufacturer"),
        "composition": result.get("composition"),
        "visible_text": result.get("visible_text"),
        "catalogue_match": result.get("catalogue_match"),
        "identity_status": result.get("identity_status"),
        "ambiguity_reason": result.get("ambiguity_reason"),
        "catalogue_confidence": result.get("catalogue_confidence"),
        "model_used": result.get("model_used")
    })


@csrf_exempt
def api_expiry_view(request):
    """POST /api/medicine/expiry: Back packaging expiry date region detection & OCR extraction."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)

    img_file = request.FILES.get('back_image') or request.FILES.get('image')
    if not img_file:
        return JsonResponse({'error': 'Missing back_image in request form-data'}, status=400)

    temp_dir = Path(settings.MEDIA_ROOT) / "temp_api"
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_stem = f"expiry_{uuid.uuid4().hex[:8]}"
    temp_path = temp_dir / f"{file_stem}_{img_file.name}"

    with open(temp_path, "wb") as f:
        for chunk in img_file.chunks():
            f.write(chunk)

    try:
        result = analyze_back_expiry(temp_path, output_dir=temp_dir, file_stem=file_stem)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return JsonResponse({
        "status": "success" if result.get("success") else "error",
        "mfg_raw": result.get("mfg_date_raw"),
        "mfg_normalized": result.get("mfg_date_normalized"),
        "exp_raw": result.get("exp_date_raw"),
        "exp_normalized": result.get("exp_date_normalized"),
        "parsed_expiry_date": str(result.get("parsed_expiry_date")) if result.get("parsed_expiry_date") else None,
        "expiry_status": result.get("expiry_status"),
        "confidence": result.get("confidence"),
        "raw_ocr_text": result.get("raw_ocr_text"),
        "warnings": result.get("warnings", [])
    })


@csrf_exempt
def api_analyze_view(request):
    """
    POST /api/medicine/analyze: Combined dual-image workflow (plan.md Section 8).
    Accepts front_image and back_image, extracts medicine identity & expiry,
    retrieves verified CDSCO disposal recommendation.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)

    front_file = request.FILES.get('front_image')
    back_file = request.FILES.get('back_image') or request.FILES.get('image')

    if not front_file and not back_file:
        return JsonResponse({'error': 'Please provide front_image and/or back_image'}, status=400)

    request_id = uuid.uuid4().hex
    output_dir = Path(settings.MEDIA_ROOT) / "api_analyze" / request_id
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    medicine_data = {
        "name": None,
        "manufacturer": None,
        "composition": None,
        "strength": None,
        "dosage_form": None,
        "identity_status": "unconfirmed"
    }
    date_data = {
        "mfg_raw": None,
        "mfg_normalized": None,
        "exp_raw": None,
        "exp_normalized": None,
        "parsed_expiry_date": None,
        "expiry_status": "unconfirmed"
    }

    # 1. Front Analysis
    if front_file:
        front_path = output_dir / f"front_{front_file.name}"
        with open(front_path, "wb") as f:
            for chunk in front_file.chunks():
                f.write(chunk)
        front_res = identify_front_medicine(front_path)
        medicine_data = {
            "name": front_res.get("visible_medicine_name"),
            "manufacturer": front_res.get("manufacturer"),
            "composition": front_res.get("composition"),
            "strength": front_res.get("strength"),
            "dosage_form": front_res.get("dosage_form"),
            "identity_status": front_res.get("identity_status", "unconfirmed")
        }
        if front_res.get("ambiguity_reason"):
            warnings.append(front_res["ambiguity_reason"])
    else:
        warnings.append("No front image provided; medicine identity unverified.")

    # 2. Back Analysis
    if back_file:
        back_path = output_dir / f"back_{back_file.name}"
        with open(back_path, "wb") as f:
            for chunk in back_file.chunks():
                f.write(chunk)
        back_res = analyze_back_expiry(back_path, output_dir=output_dir, file_stem=f"api_{request_id}")
        date_data = {
            "mfg_raw": back_res.get("mfg_date_raw"),
            "mfg_normalized": back_res.get("mfg_date_normalized"),
            "exp_raw": back_res.get("exp_date_raw"),
            "exp_normalized": back_res.get("exp_date_normalized"),
            "parsed_expiry_date": str(back_res.get("parsed_expiry_date")) if back_res.get("parsed_expiry_date") else None,
            "expiry_status": back_res.get("expiry_status", "unconfirmed")
        }
        warnings.extend(back_res.get("warnings", []))
    else:
        warnings.append("No back image provided; expiry status unverified.")

    # 3. Disposal Recommendation Lookup
    disposal_rule = get_disposal_rule(
        status=date_data["expiry_status"],
        medicine_name=medicine_data["name"] or "",
        composition=medicine_data["composition"] or "",
        dosage_form=medicine_data["dosage_form"] or ""
    )

    return JsonResponse({
        "request_id": request_id,
        "medicine": medicine_data,
        "dates": date_data,
        "disposal": {
            "rule_id": disposal_rule.get("rule_id"),
            "category": disposal_rule.get("medicine_category"),
            "recommendation": disposal_rule.get("approved_action"),
            "precautions": disposal_rule.get("precautions"),
            "source_title": disposal_rule.get("source_title"),
            "source_url": disposal_rule.get("source_url"),
            "source_section": disposal_rule.get("source_section")
        },
        "warnings": warnings,
        "disclaimer": "This tool is a prototype waste identifier and does not constitute medical, diagnosis, or clinical advice."
    })


@require_GET
def api_disposal_rules_view(request):
    """GET /api/disposal-rules: Returns all verified CDSCO 2025 disposal rules."""
    rules = get_all_disposal_rules()
    return JsonResponse({"status": "success", "count": len(rules), "rules": rules})


@require_GET
def api_health_view(request):
    """GET /api/health: System health, model readiness, and dataset catalogue status."""
    cat_records = load_catalogue()
    openai_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())

    return JsonResponse({
        "status": "healthy",
        "service": "Medicine Waste Identifier",
        "catalogue_loaded": len(cat_records) > 0,
        "catalogue_records_count": len(cat_records),
        "openai_vision_configured": openai_configured,
        "vision_model": os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        "yolo_model": "yolov8n_best",
        "disposal_rules_count": len(get_all_disposal_rules())
    })


@csrf_exempt
def api_scan_view(request):
    """Legacy endpoint: redirects to api_analyze_view for backward compatibility."""
    return api_analyze_view(request)
