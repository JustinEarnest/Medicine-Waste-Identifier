from django.contrib import admin
from django.utils.html import format_html
from .models import ScanRecord


@admin.register(ScanRecord)
class ScanRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'front_preview_thumbnail',
        'back_preview_thumbnail',
        'medicine_name',
        'identity_badge',
        'status_badge',
        'exp_date',
        'disposal_rule_id',
        'is_reviewed',
        'created_at',
    )
    list_filter = ('status', 'identity_status', 'is_reviewed', 'created_at')
    search_fields = ('medicine_name', 'manufacturer', 'composition', 'raw_ocr_text', 'exp_date', 'disposal_rule_id')
    readonly_fields = ('created_at', 'front_image_preview', 'back_image_preview', 'annotated_preview', 'crop_preview')
    list_editable = ('is_reviewed',)

    fieldsets = (
        ('Overview', {
            'fields': ('title', 'status', 'is_reviewed', 'created_at', 'warnings')
        }),
        ('Front Identification (OpenAI / Catalogue)', {
            'fields': (
                'medicine_name', 'manufacturer', 'composition', 'dosage_form',
                'strength', 'identity_status', 'catalogue_confidence', 'raw_front_text'
            )
        }),
        ('Back Expiry Findings (YOLOv8 + EasyOCR)', {
            'fields': ('exp_date', 'mfg_date', 'parsed_expiry_date', 'confidence', 'raw_ocr_text')
        }),
        ('Packaging Visuals', {
            'fields': (
                'front_image', 'front_image_preview',
                'back_image', 'back_image_preview',
                'annotated_image', 'annotated_preview',
                'crop_image', 'crop_preview'
            )
        }),
        ('Disposal Guidance (CDSCO 2025)', {
            'fields': (
                'disposal_rule_id', 'disposal_category', 'disposal_guidance',
                'disposal_precautions', 'disposal_source_url', 'disposal_source_section',
                'illness_info', 'admin_notes'
            )
        }),
    )

    def front_preview_thumbnail(self, obj):
        img = obj.effective_front_image
        if img:
            return format_html(
                '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px;" title="Front View" />',
                img.url
            )
        return "-"
    front_preview_thumbnail.short_description = "Front"

    def back_preview_thumbnail(self, obj):
        img = obj.effective_back_image
        if img:
            return format_html(
                '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px;" title="Back View" />',
                img.url
            )
        return "-"
    back_preview_thumbnail.short_description = "Back"

    def identity_badge(self, obj):
        colors = {
            'confirmed': ('#10b981', '#064e3b'),
            'ambiguous': ('#f59e0b', '#78350f'),
            'unconfirmed': ('#6b7280', '#1f2937'),
        }
        bg, text = colors.get(obj.identity_status, ('#6b7280', '#1f2937'))
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 9999px; font-weight: 600; font-size: 10px;">{}</span>',
            bg, obj.get_identity_status_display()
        )
    identity_badge.short_description = "Identity"

    def status_badge(self, obj):
        colors = {
            'VALID': ('#10b981', '#064e3b'),
            'EXPIRED': ('#ef4444', '#7f1d1d'),
            'REVIEW': ('#f59e0b', '#78350f'),
        }
        bg, text = colors.get(obj.status, ('#6b7280', '#1f2937'))
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 11px;">{}</span>',
            bg, obj.get_status_display()
        )
    status_badge.short_description = "Expiry"

    def front_image_preview(self, obj):
        img = obj.effective_front_image
        if img:
            return format_html('<img src="{}" style="max-height: 220px; border-radius: 8px;" />', img.url)
        return "No front image"

    def back_image_preview(self, obj):
        img = obj.effective_back_image
        if img:
            return format_html('<img src="{}" style="max-height: 220px; border-radius: 8px;" />', img.url)
        return "No back image"

    def annotated_preview(self, obj):
        if obj.annotated_image:
            return format_html('<img src="{}" style="max-height: 220px; border-radius: 8px;" />', obj.annotated_image.url)
        return "No detection overlay"

    def crop_preview(self, obj):
        if obj.crop_image:
            return format_html('<img src="{}" style="max-height: 180px; border-radius: 8px;" />', obj.crop_image.url)
        return "No crop"
