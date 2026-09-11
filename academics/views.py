# academics/views.py
from rest_framework import viewsets, permissions
from .models import GradeLevel, Classroom, Subject, SubjectAssignment, StudentEnrollment, TimetableSlot
from .serializers import (
    GradeLevelSerializer, ClassroomSerializer, SubjectSerializer, 
    SubjectAssignmentSerializer, StudentEnrollmentSerializer, TimetableSlotSerializer
)

class GradeLevelViewSet(viewsets.ModelViewSet):
    serializer_class = GradeLevelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GradeLevel.objects.filter(school=self.request.user.school)

class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Classroom.objects.filter(school=self.request.user.school)

class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subject.objects.filter(school=self.request.user.school)

class SubjectAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubjectAssignment.objects.filter(school=self.request.user.school)

class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentEnrollment.objects.filter(school=self.request.user.school)

class TimetableSlotViewSet(viewsets.ModelViewSet):
    serializer_class = TimetableSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TimetableSlot.objects.filter(school=self.request.user.school)