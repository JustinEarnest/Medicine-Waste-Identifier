from django.urls import path
from . import views

app_name = 'waste_identifier'

urlpatterns = [
    # Web UI Routes
    path('', views.home_view, name='home'),
    path('scan/upload/', views.scan_upload_view, name='scan_upload'),
    path('scan/sample/', views.sample_scan_view, name='sample_scan'),
    path('scan/<int:pk>/', views.scan_detail_view, name='scan_detail'),
    path('scan/<int:pk>/confirm-name/', views.confirm_name_view, name='confirm_name'),
    path('scan/<int:pk>/review/', views.mark_reviewed_view, name='mark_reviewed'),
    path('history/', views.history_view, name='history'),
    path('disposal-guide/', views.disposal_guide_view, name='disposal_guide'),

    # REST API Routes (plan.md Section 8)
    path('api/medicine/identify', views.api_identify_view, name='api_identify'),
    path('api/medicine/expiry', views.api_expiry_view, name='api_expiry'),
    path('api/medicine/analyze', views.api_analyze_view, name='api_analyze'),
    path('api/disposal-rules', views.api_disposal_rules_view, name='api_disposal_rules'),
    path('api/health', views.api_health_view, name='api_health'),
    path('api/scan/', views.api_scan_view, name='api_scan'),
]
