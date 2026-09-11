from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.apps import apps
from django.db.models import Q, Avg
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response


# ==========================================
# Helper Utilities
# ==========================================

def get_model_safely(app_label, model_name):
    """Safely fetch a model without throwing errors if the app or model does not exist."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def get_tenant_from_request(request):
    """Fallback tenant finder if domain/subdomain middleware is used."""
    if hasattr(request, 'tenant'):
        return request.tenant
    return None


# ==========================================
# Django UI Views
# ==========================================

def home(request):
    """Home page view; redirects logged-in users to their respective dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    return render(request, 'schools/home.html')


@login_required
def dashboard_redirect(request):
    """Redirects authenticated users to their role-specific dashboard."""
    user = request.user
    role = getattr(user, 'role', None) or getattr(user, 'user_type', None)

    if role in ['ADMIN', 'SCHOOL_ADMIN'] or user.is_staff or user.is_superuser:
        return redirect('school_admin_dashboard')
    elif role == 'TEACHER' or hasattr(user, 'teacher_profile'):
        return redirect('teacher_dashboard')

    return redirect('student_dashboard')


@login_required
def school_admin_dashboard(request):
    """Dashboard view for school administrators."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    context = {'school': school}
    return render(request, 'dashboard/admin.html', context)


@login_required
def teacher_dashboard(request):
    """Dashboard view for teachers."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    context = {'school': school}
    return render(request, 'dashboard/teacher.html', context)


@login_required
def profile_edit_view(request):
    """View to handle profile updates for all user types."""
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)

        if 'profile_picture' in request.FILES and hasattr(user, 'profile_picture'):
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile_edit')

    return render(request, 'accounts/profile_edit.html', {'user': user})


@login_required
def exam_results_view(request):
    """View for viewing exam results and report cards."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/exam_results.html', {'school': school})


@login_required
def assignments_list_view(request):
    """View for viewing coursework and assignment lists."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/assignments_list.html', {'school': school})


@login_required
def attendance_record_view(request):
    """View for checking presence logs and attendance history."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/attendance_record.html', {'school': school})


import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.utils import timezone

# Direct imports based on project structure
from accounts.models import StudentProfile, CustomUser
from students.models import Attendance
from academics.models import Classroom, SubjectAssignment
from schools.models import School, Term, AcademicYear

logger = logging.getLogger(__name__)


def get_model_safely(app_label, model_name):
    """Utility helper to import models safely if app names vary."""
    from django.apps import apps
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


@login_required
def student_dashboard(request):
    user = request.user
    school = getattr(user, 'school', None)

    # 1. Retrieve StudentProfile
    student_profile = getattr(user, 'student_profile', None)
    if not student_profile:
        student_profile = StudentProfile.objects.filter(user=user).first()

    # 2. Resolve Enrollment, Class, and Enrolled Courses
    grade_level = None
    enrolled_courses = []

    if student_profile:
        # Get active enrollment (pre-fetching classroom and grade level)
        enrollment = (
            student_profile.enrollments.filter(academic_year__is_current=True)
            .select_related('classroom__grade_level', 'academic_year')
            .first()
            or student_profile.enrollments.select_related('classroom__grade_level')
            .order_by('-enrolled_at')
            .first()
        )

        if enrollment and enrollment.classroom:
            classroom = enrollment.classroom
            # Combine Grade Level name and Stream name (e.g., "Form 1 East")
            if classroom.grade_level:
                grade_level = f"{classroom.grade_level.name} {classroom.name}".strip()
            else:
                grade_level = classroom.name

            # Fetch enrolled subjects mapped to this classroom & academic year
            assignments = (
                SubjectAssignment.objects.filter(
                    classroom=classroom,
                    academic_year=enrollment.academic_year
                )
                .select_related('subject', 'teacher__user')
            )

            enrolled_courses = [
                {
                    "name": sa.subject.name,
                    "code": sa.subject.code,
                    "teacher": sa.teacher.user if sa.teacher else None,
                }
                for sa in assignments
            ]

    # Fallback to Attendance if no enrollment record exists
    if not grade_level and student_profile:
        latest_attendance = Attendance.objects.filter(student=student_profile).select_related('classroom__grade_level').first()
        if latest_attendance and latest_attendance.classroom:
            cls = latest_attendance.classroom
            grade_level = f"{cls.grade_level.name} {cls.name}".strip() if cls.grade_level else cls.name

    # 3. Resolve Student ID
    student_id = student_profile.admission_number if student_profile else user.username

    context = {
        "school": school,
        "student_profile": student_profile,
        "grade_level": grade_level or "Unassigned Class",
        "student_id": student_id,
        "enrolled_courses": enrolled_courses,
        "recent_results": [],
        "pending_assignments": [],
        "announcements": [],
        "overall_gpa": "N/A",
        "attendance_rate": "N/A",
        "pending_tasks_count": 0,
    }

    return render(request, 'dashboard/student.html', context)

# ==========================================
# REST Framework API Views & ViewSets
# ==========================================

class SchoolDomainInfoView(APIView):
    """API view that returns current school domain and tenant information."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        school = get_tenant_from_request(request)
        if not school and hasattr(request, 'user') and request.user.is_authenticated:
            school = getattr(request.user, 'school', None)

        school_name = getattr(school, 'name', None) or 'Default School'
        domain = request.get_host()

        return Response({
            'domain': domain,
            'school_name': school_name,
            'is_active': True,
        })


class DynamicBaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet that dynamically binds to target models safely."""

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    model_name = None

    def get_queryset(self):
        if self.model_name:
            Model = (
                get_model_safely('schools', self.model_name)
                or get_model_safely('academics', self.model_name)
                or get_model_safely('core', self.model_name)
                or get_model_safely('accounts', self.model_name)
            )
            if Model:
                return Model.objects.all()
        return []

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not hasattr(queryset, 'model'):
            return Response([])
        return super().list(request, *args, **kwargs)


class SchoolViewSet(DynamicBaseViewSet):
    """API endpoint for Schools."""

    model_name = 'School'


class SchoolSettingViewSet(DynamicBaseViewSet):
    """API endpoint for School Settings."""

    model_name = 'SchoolSetting'


class AcademicYearViewSet(DynamicBaseViewSet):
    """API endpoint for Academic Years."""

    model_name = 'AcademicYear'


class TermViewSet(DynamicBaseViewSet):
    """API endpoint for Academic Terms."""

    model_name = 'Term'


class ClassViewSet(DynamicBaseViewSet):
    """API endpoint for Classes/Grades."""

    model_name = 'Class'


class SubjectViewSet(DynamicBaseViewSet):
    """API endpoint for Subjects/Courses."""

    model_name = 'Subject'


class DepartmentViewSet(DynamicBaseViewSet):
    """API endpoint for Departments."""

    model_name = 'Department'


class StudentViewSet(DynamicBaseViewSet):
    """API endpoint for Students."""

    model_name = 'StudentProfile'


class TeacherViewSet(DynamicBaseViewSet):
    """API endpoint for Teachers."""

    model_name = 'TeacherProfile'


class FacilityViewSet(DynamicBaseViewSet):
    """API endpoint for School Facilities."""

    model_name = 'Facility'