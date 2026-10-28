from django.db import models
from django.utils import timezone


class ScanRecord(models.Model):
    STATUS_CHOICES = [
        ('VALID', 'Valid (Not Expired)'),
        ('EXPIRED', 'Expired'),
        ('REVIEW', 'Expiry Unknown / Needs Review'),
    ]

    IDENTITY_CHOICES = [
        ('confirmed', 'Confirmed in Catalogue'),
        ('ambiguous', 'Ambiguous Candidates'),
        ('unconfirmed', 'Unconfirmed / Unreadable'),
    ]

    title = models.CharField(max_length=200, default='Medicine Scan')
    
    # Dual Packaging Uploads (plan.md Phase 6)
    front_image = models.ImageField(upload_to='scans/front/%Y/%m/', blank=True, null=True, help_text="Front package view for medicine identification")
    back_image = models.ImageField(upload_to='scans/back/%Y/%m/', blank=True, null=True, help_text="Back package view for expiry text region")
    # Legacy single image support
    image = models.ImageField(upload_to='scans/%Y/%m/', blank=True, null=True)

    annotated_image = models.ImageField(upload_to='annotated/%Y/%m/', blank=True, null=True)
    crop_image = models.ImageField(upload_to='crops/%Y/%m/', blank=True, null=True)

    # Front-side Identification Fields
    medicine_name = models.CharField(max_length=200, blank=True, default='Unconfirmed Medicine')
    manufacturer = models.CharField(max_length=200, blank=True, default='')
    composition = models.TextField(blank=True, default='')
    dosage_form = models.CharField(max_length=100, blank=True, default='')
    strength = models.CharField(max_length=100, blank=True, default='')
    identity_status = models.CharField(max_length=30, choices=IDENTITY_CHOICES, default='unconfirmed')
    catalogue_confidence = models.FloatField(default=0.0)
    raw_front_text = models.TextField(blank=True, help_text="Raw OCR text extracted from front image")

    # Back-side Expiry Fields
    raw_ocr_text = models.TextField(blank=True, help_text="Full OCR extracted text from detected back region")
    mfg_date = models.CharField(max_length=60, blank=True, help_text="Manufacturing date candidate")
    exp_date = models.CharField(max_length=60, blank=True, help_text="Expiry date candidate")
    parsed_expiry_date = models.DateField(null=True, blank=True, help_text="Standardized ISO date")

    # Overall Status & Confidence
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='REVIEW')
    confidence = models.FloatField(default=0.0, help_text="Model detection / OCR average confidence")

    # Clinical Indications & Verified Disposal (CDSCO 2025)
    illness_info = models.TextField(blank=True, help_text="Common medical uses and indications")
    disposal_guidance = models.TextField(blank=True, help_text="Approved disposal action")
    disposal_rule_id = models.CharField(max_length=60, blank=True, default='')
    disposal_category = models.CharField(max_length=120, blank=True, default='')
    disposal_precautions = models.TextField(blank=True, default='')
    disposal_source_url = models.URLField(blank=True, default='')
    disposal_source_section = models.CharField(max_length=250, blank=True, default='')

    # Discrepancy Warnings & Operator Verification
    warnings = models.TextField(blank=True, default='', help_text="Audit and discrepancy warnings")
    is_reviewed = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Medicine Scan'
        verbose_name_plural = 'Medicine Scans'

    def __str__(self):
        return f"{self.medicine_name} ({self.get_status_display()}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def effective_front_image(self):
        return self.front_image if self.front_image else self.image

    @property
    def effective_back_image(self):
        return self.back_image if self.back_image else self.image
