import json
import io
from pathlib import Path
from PIL import Image
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import ScanRecord
from .services.catalogue import match_catalogue
from .services.disposal_rules import get_disposal_rule, get_all_disposal_rules


def create_dummy_image(color=(200, 200, 200), size=(100, 100)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class CatalogueAndDisposalTests(TestCase):
    def test_catalogue_exact_match(self):
        res = match_catalogue("Augmentin 625 Duo Tablet")
        self.assertEqual(res["status"], "confirmed")
        self.assertIsNotNone(res["match"])
        self.assertIn("Amoxycillin", res["match"]["composition"])

    def test_catalogue_fuzzy_match(self):
        res = match_catalogue("augmentin 625 duo")
        self.assertIn(res["status"], ["confirmed", "ambiguous"])
        self.assertIsNotNone(res["match"])
        self.assertIn("Augmentin", res["match"]["name"])

    def test_catalogue_safe_abstention(self):
        res = match_catalogue("completely_random_unknown_substance_xyz")
        self.assertEqual(res["status"], "unconfirmed")
        self.assertIsNone(res["match"])

    def test_disposal_rules_antibiotic(self):
        rule = get_disposal_rule(status="EXPIRED", medicine_name="Amoxycillin and Potassium Clavulanate")
        self.assertEqual(rule["rule_id"], "DISP-ANTIBIOTIC-01")
        self.assertIn("Antimicrobial", rule["source_section"])

    def test_disposal_rules_cytotoxic(self):
        rule = get_disposal_rule(status="EXPIRED", medicine_name="Avastin 400mg Injection")
        self.assertEqual(rule["rule_id"], "DISP-CYTOTOXIC-04")
        self.assertIn("Cytotoxic", rule["medicine_category"])

    def test_disposal_rules_valid(self):
        rule = get_disposal_rule(status="VALID", medicine_name="Paracetamol")
        self.assertEqual(rule["rule_id"], "DISP-VALID-08")

    def test_disposal_rules_uncertain(self):
        rule = get_disposal_rule(status="REVIEW", medicine_name="Unknown Strip")
        self.assertEqual(rule["rule_id"], "DISP-UNCERTAIN-09")


class ViewAndAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get(reverse('waste_identifier:api_health'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["catalogue_loaded"])
        self.assertGreater(data["catalogue_records_count"], 10000)

    def test_disposal_rules_endpoint(self):
        response = self.client.get(reverse('waste_identifier:api_disposal_rules'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["count"], 9)

    def test_home_page_view(self):
        response = self.client.get(reverse('waste_identifier:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-Image Medicine Packaging Scanner")

    def test_disposal_guide_page_view(self):
        response = self.client.get(reverse('waste_identifier:disposal_guide'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CDSCO")

    def test_history_page_view(self):
        response = self.client.get(reverse('waste_identifier:history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scan History")

    def test_scan_detail_and_confirm_name(self):
        dummy_front = SimpleUploadedFile("front.jpg", create_dummy_image(), content_type="image/jpeg")
        dummy_back = SimpleUploadedFile("back.jpg", create_dummy_image(), content_type="image/jpeg")

        scan = ScanRecord.objects.create(
            title="Test Package",
            front_image=dummy_front,
            back_image=dummy_back,
            medicine_name="Augmentin 625 Duo Tablet",
            status="EXPIRED",
            exp_date="12/2024"
        )

        detail_res = self.client.get(reverse('waste_identifier:scan_detail', kwargs={'pk': scan.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Augmentin 625 Duo Tablet")

        # Test manual name update
        update_res = self.client.post(
            reverse('waste_identifier:confirm_name', kwargs={'pk': scan.pk}),
            {'medicine_name': 'Azithral 500 Tablet'},
            follow=True
        )
        self.assertEqual(update_res.status_code, 200)
        scan.refresh_from_db()
        self.assertEqual(scan.medicine_name, "Azithral 500 Tablet")
        self.assertEqual(scan.identity_status, "confirmed")
        self.assertEqual(scan.disposal_rule_id, "DISP-ANTIBIOTIC-01")
