import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from waste_identifier.models import ScanRecord
from waste_identifier.services.pipeline import process_medicine_image


class Command(BaseCommand):
    help = "Seeds initial sample scans from test images"

    def handle(self, *args, **options):
        test_dir = settings.BASE_DIR / "dataset" / "roboflow_export" / "test" / "images"
        if not test_dir.is_dir():
            self.stdout.write(self.style.WARNING(f"Directory {test_dir} not found."))
            return

        samples = sorted(test_dir.glob("*.jpg"))[:3]
        self.stdout.write(f"Processing {len(samples)} sample images...")

        for img_path in samples:
            with open(img_path, "rb") as f:
                scan = ScanRecord.objects.create(
                    title=f"Sample: {img_path.stem[:20]}",
                    image=ContentFile(f.read(), name=img_path.name)
                )

            out_dir = Path(settings.MEDIA_ROOT) / "processed" / str(scan.id)
            res = process_medicine_image(Path(scan.image.path), out_dir, f"scan_{scan.id}")

            if res.get("success"):
                scan.annotated_image = f"processed/{scan.id}/{res['annotated_filename']}"
                scan.crop_image = f"processed/{scan.id}/{res['crop_filename']}"
                scan.medicine_name = res.get("medicine_name", "Medicine Package")
                scan.raw_ocr_text = res.get("raw_ocr_text", "")
                scan.exp_date = res.get("exp_date", "")
                scan.mfg_date = res.get("mfg_date", "")
                scan.parsed_expiry_date = res.get("parsed_expiry_date")
                scan.status = res.get("status", "REVIEW")
                scan.confidence = res.get("confidence", 0.0)
                scan.illness_info = res.get("illness_info", "")
                scan.disposal_guidance = res.get("disposal_guidance", "")
                scan.save()
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Scan #{scan.id} saved: Status={scan.status}, EXP={scan.exp_date or 'N/A'}"
                ))

        self.stdout.write(self.style.SUCCESS("All samples seeded successfully!"))
