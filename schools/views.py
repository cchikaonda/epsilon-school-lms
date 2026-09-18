import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.apps import apps
from django.db.models import Q, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.models import StudentProfile, CustomUser
from students.models import Attendance
from academics.models import Classroom, SubjectAssignment, Subject
from schools.models import School, Term, AcademicYear
from .forms import SchoolForm, UserManagementForm

logger = logging.getLogger(__name__)
User = get_user_model()


# ==========================================
# Helper Utilities & Permissions
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


def is_system_admin(user):
    """Check if user has platform super administrator permissions."""
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', None) in ['SUPER_ADMIN', 'ADMIN']
    )


# ==========================================
# Authentication & Navigation Routing
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

    if user.is_superuser or role in ['ADMIN', 'SUPER_ADMIN']:
        return redirect('system_admin_dashboard')
    elif role == 'SCHOOL_ADMIN' or (user.is_staff and getattr(user, 'school', None)):
        return redirect('school_admin_dashboard')
    elif role == 'ACCOUNTANT' or hasattr(user, 'accountant_profile'):
        return redirect('accountant_dashboard')
    elif role == 'PARENT' or hasattr(user, 'parent_profile'):
        return redirect('parent_dashboard')
    elif role == 'TEACHER' or hasattr(user, 'teacher_profile'):
        return redirect('teacher_dashboard')

    return redirect('student_dashboard')


# ==========================================
# System Admin Management (Full CRUD)
# ==========================================

@login_required
@user_passes_test(is_system_admin)
def system_admin_dashboard(request):
    """Main control center displaying metrics and overall platform data."""
    schools = School.objects.all()
    users = User.objects.all().select_related('school')
    
    context = {
        'schools': schools,
        'schools_count': schools.count(),
        'users_count': users.count(),
        'recent_users': users.order_by('-date_joined')[:10],
    }
    return render(request, 'dashboard/system_admin.html', context)


# --- School CRUD ---

@login_required
@user_passes_test(is_system_admin)
def school_list_create_view(request):
    """List all schools and handle creation of new school tenants."""
    schools = School.objects.all()
    form = SchoolForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'School tenant provisioned successfully!')
        return redirect('school_manage')

    return render(request, 'dashboard/schools_manage.html', {'schools': schools, 'form': form})


@login_required
@user_passes_test(is_system_admin)
def school_edit_view(request, pk):
    """Update details for a specific school."""
    school = get_object_or_404(School, pk=pk)
    form = SchoolForm(request.POST or None, instance=school)
    
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'School "{school.name}" updated successfully!')
        return redirect('school_manage')

    return render(request, 'dashboard/school_form.html', {'form': form, 'school': school})


@login_required
@user_passes_test(is_system_admin)
def school_delete_view(request, pk):
    """Delete a school tenant."""
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school_name = school.name
        school.delete()
        messages.success(request, f'School "{school_name}" deleted successfully.')
        return redirect('school_manage')
        
    return render(request, 'dashboard/confirm_delete.html', {'object': school, 'type': 'School'})


# --- User CRUD ---

@login_required
@user_passes_test(is_system_admin)
def user_list_create_view(request):
    """List system users and handle creation of new user accounts."""
    users = User.objects.all().select_related('school')
    form = UserManagementForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User account created successfully!')
        return redirect('user_manage')

    return render(request, 'dashboard/users_manage.html', {'users': users, 'form': form})


@login_required
@user_passes_test(is_system_admin)
def user_edit_view(request, pk):
    """Edit user profiles, roles, and assigned schools."""
    user_obj = get_object_or_404(User, pk=pk)
    form = UserManagementForm(request.POST or None, instance=user_obj)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'User "{user_obj.username}" updated successfully!')
        return redirect('user_manage')

    return render(request, 'dashboard/user_form.html', {'form': form, 'user_obj': user_obj})


@login_required
@user_passes_test(is_system_admin)
def user_delete_view(request, pk):
    """Remove a user account from the system."""
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'User account "{username}" deleted.')
        return redirect('user_manage')

    return render(request, 'dashboard/confirm_delete.html', {'object': user_obj, 'type': 'User'})


# ==========================================
# Role-Specific Dashboard Views
# ==========================================

@login_required
def school_admin_dashboard(request):
    """Dashboard view for school-level administrators."""
    user = request.user
    role = getattr(user, 'role', None) or getattr(user, 'user_type', None)

    if user.is_superuser or role in ['ADMIN', 'SUPER_ADMIN']:
        school_id = request.GET.get('school_id')
        school = School.objects.filter(id=school_id).first() if school_id else None
        is_global_admin = True
    else:
        school = getattr(user, 'school', None) or get_tenant_from_request(request)
        is_global_admin = False

    context = {
        'school': school,
        'is_global_admin': is_global_admin,
    }
    return render(request, 'dashboard/school_admin.html', context)


@login_required
def accountant_dashboard(request):
    """Dashboard view for school accountants."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'dashboard/accountant.html', {'school': school})


@login_required
def parent_dashboard(request):
    """Dashboard view for parents to view linked children."""
    user = request.user
    school = getattr(user, 'school', None) or get_tenant_from_request(request)
    parent_profile = getattr(user, 'parent_profile', None)
    children = parent_profile.children.all() if parent_profile and hasattr(parent_profile, 'children') else []

    context = {
        'school': school,
        'parent_profile': parent_profile,
        'children': children,
    }
    return render(request, 'dashboard/parent.html', context)


@login_required
def teacher_dashboard(request):
    """Dashboard view for teachers."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'dashboard/teacher.html', {'school': school})


@login_required
def student_dashboard(request):
    """Dashboard view for students."""
    user = request.user
    school = getattr(user, 'school', None) or get_tenant_from_request(request)

    student_profile = getattr(user, 'student_profile', None)
    if not student_profile:
        student_profile = StudentProfile.objects.filter(user=user).first()

    grade_level = None
    enrolled_courses = []

    if student_profile:
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
            grade_level = (
                f"{classroom.grade_level.name} {classroom.name}".strip()
                if classroom.grade_level else classroom.name
            )

            assignments = SubjectAssignment.objects.filter(
                classroom=classroom,
                academic_year=enrollment.academic_year
            ).select_related('subject', 'teacher__user')

            enrolled_courses = [
                {
                    "name": sa.subject.name,
                    "code": sa.subject.code,
                    "teacher": sa.teacher.user if sa.teacher else None,
                }
                for sa in assignments
            ]

    if not grade_level and student_profile:
        latest_attendance = Attendance.objects.filter(student=student_profile).select_related('classroom__grade_level').first()
        if latest_attendance and latest_attendance.classroom:
            cls = latest_attendance.classroom
            grade_level = f"{cls.grade_level.name} {cls.name}".strip() if cls.grade_level else cls.name

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
# Additional Feature Views
# ==========================================

@login_required
def profile_edit_view(request):
    """Handles profile updates for users."""
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
    """View exam results and report cards."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/exam_results.html', {'school': school})


@login_required
def assignments_list_view(request):
    """View coursework and assignments."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/assignments_list.html', {'school': school})


@login_required
def attendance_record_view(request):
    """Check attendance records."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    return render(request, 'academics/attendance_record.html', {'school': school})


# ==========================================
# REST Framework API Views & ViewSets
# ==========================================

class SchoolDomainInfoView(APIView):
    """API view returning current school domain and tenant information."""

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
    """Base ViewSet dynamically binding target models safely and enforcing multi-tenant scoping."""

    permission_classes = [permissions.IsAuthenticated]
    model_name = None

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return []

        if self.model_name:
            Model = (
                get_model_safely('schools', self.model_name)
                or get_model_safely('academics', self.model_name)
                or get_model_safely('core', self.model_name)
                or get_model_safely('accounts', self.model_name)
            )
            if Model:
                queryset = Model.objects.all()
                role = getattr(user, 'role', None) or getattr(user, 'user_type', None)

                if user.is_superuser or role in ['ADMIN', 'SUPER_ADMIN']:
                    return queryset

                school = getattr(user, 'school', None) or get_tenant_from_request(self.request)
                if school and hasattr(Model, 'school'):
                    return queryset.filter(school=school)

                return queryset
        return []

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not hasattr(queryset, 'model'):
            return Response([])
        return super().list(request, *args, **kwargs)


class SchoolViewSet(DynamicBaseViewSet):
    model_name = 'School'

class SchoolSettingViewSet(DynamicBaseViewSet):
    model_name = 'SchoolSetting'

class AcademicYearViewSet(DynamicBaseViewSet):
    model_name = 'AcademicYear'

class TermViewSet(DynamicBaseViewSet):
    model_name = 'Term'

class ClassViewSet(DynamicBaseViewSet):
    model_name = 'Class'

class SubjectViewSet(DynamicBaseViewSet):
    model_name = 'Subject'

class DepartmentViewSet(DynamicBaseViewSet):
    model_name = 'Department'

class StudentViewSet(DynamicBaseViewSet):
    model_name = 'StudentProfile'

class TeacherViewSet(DynamicBaseViewSet):
    model_name = 'TeacherProfile'

class ParentViewSet(DynamicBaseViewSet):
    model_name = 'ParentProfile'

class FacilityViewSet(DynamicBaseViewSet):
    model_name = 'Facility'