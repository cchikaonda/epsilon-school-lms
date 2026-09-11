# academics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GradeLevelViewSet, ClassroomViewSet, SubjectViewSet, 
    SubjectAssignmentViewSet, StudentEnrollmentViewSet, TimetableSlotViewSet
)

router = DefaultRouter()
router.register(r'grade-levels', GradeLevelViewSet, basename='grade-level')
router.register(r'classrooms', ClassroomViewSet, basename='classroom')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'subject-assignments', SubjectAssignmentViewSet, basename='subject-assignment')
router.register(r'enrollments', StudentEnrollmentViewSet, basename='enrollment')
router.register(r'timetable-slots', TimetableSlotViewSet, basename='timetable-slot')

urlpatterns = [path('', include(router.urls))]