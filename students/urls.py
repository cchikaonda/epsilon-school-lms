# students/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentMedicalRecordViewSet, ParentRelationshipViewSet, 
    AttendanceViewSet, StudentDocumentViewSet, IncidentReportViewSet
)

router = DefaultRouter()
router.register(r'medical-records', StudentMedicalRecordViewSet, basename='medical-record')
router.register(r'parent-relationships', ParentRelationshipViewSet, basename='parent-relationship')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'documents', StudentDocumentViewSet, basename='document')
router.register(r'incident-reports', IncidentReportViewSet, basename='incident-report')

urlpatterns = [path('', include(router.urls))]