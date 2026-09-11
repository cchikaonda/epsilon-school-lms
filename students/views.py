# students/views.py
from rest_framework import viewsets, permissions
from .models import StudentMedicalRecord, ParentRelationship, Attendance, StudentDocument, IncidentReport
from .serializers import (
    StudentMedicalRecordSerializer, ParentRelationshipSerializer, 
    AttendanceSerializer, StudentDocumentSerializer, IncidentReportSerializer
)

class StudentMedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = StudentMedicalRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentMedicalRecord.objects.filter(school=self.request.user.school)

class ParentRelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = ParentRelationshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ParentRelationship.objects.filter(school=self.request.user.school)

class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Attendance.objects.filter(school=self.request.user.school)

class StudentDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentDocument.objects.filter(school=self.request.user.school)

class IncidentReportViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IncidentReport.objects.filter(school=self.request.user.school)