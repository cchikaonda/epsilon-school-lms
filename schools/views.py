import logging
import uuid
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

from accounts.models import StudentProfile, CustomUser, TeacherProfile, ParentProfile
from students.models import Attendance
from academics.models import GradeLevel, Classroom, SubjectAssignment, Subject
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
    school = request.user.school

    if request.method == 'POST':
        action = request.POST.get('action')

        # Action 1: Create Academic Year
        if action == 'create_academic_year':
            name = request.POST.get('name')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            is_current = request.POST.get('is_current') == 'on'

            if AcademicYear.objects.filter(school=school, name=name).exists():
                messages.error(request, f'Academic year "{name}" already exists.')
            else:
                AcademicYear.objects.create(
                    school=school,
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current
                )
                messages.success(request, f'Academic year "{name}" created successfully.')

        # Action 2: Create Grade Level
        elif action == 'create_grade_level':
            name = request.POST.get('name')
            level_order = request.POST.get('level_order', 1)

            if GradeLevel.objects.filter(school=school, name=name).exists():
                messages.error(request, f'Grade level "{name}" already exists.')
            else:
                GradeLevel.objects.create(
                    school=school,
                    name=name,
                    level_order=level_order
                )
                messages.success(request, f'Grade level "{name}" created successfully.')

        # Action 3: Create User Account
        elif action == 'create_user':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            role = request.POST.get('role')
            password = request.POST.get('password')

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, f'User with email {email} already exists.')
            else:
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    school=school
                )
                if role == 'TEACHER':
                    TeacherProfile.objects.get_or_create(user=user, school=school)
                elif role == 'STUDENT':
                    StudentProfile.objects.get_or_create(user=user, school=school)

                messages.success(request, f'Account for {user.get_full_name()} created successfully.')

        # Action 4: Create Classroom / Stream
        elif action == 'create_class':
            class_name = request.POST.get('class_name')
            grade_level_id = request.POST.get('grade_level_id')

            if grade_level_id:
                grade_level = GradeLevel.objects.get(id=grade_level_id, school=school)
            else:
                grade_level, _ = GradeLevel.objects.get_or_create(
                    school=school,
                    name="General Grade",
                    defaults={'level_order': 1}
                )

            if Classroom.objects.filter(school=school, grade_level=grade_level, name=class_name).exists():
                messages.error(request, f'Classroom "{grade_level.name} - {class_name}" already exists.')
            else:
                Classroom.objects.create(
                    school=school,
                    grade_level=grade_level,
                    name=class_name
                )
                messages.success(request, f'Classroom "{grade_level.name} - {class_name}" created successfully.')

        # Action 5: Create Subject
        elif action == 'create_subject':
            subject_name = request.POST.get('subject_name')
            code = request.POST.get('code')
            is_elective = request.POST.get('is_elective') == 'on'

            if Subject.objects.filter(school=school, code=code).exists():
                messages.error(request, f'Subject with code "{code}" already exists.')
            else:
                Subject.objects.create(
                    school=school,
                    name=subject_name,
                    code=code,
                    is_elective=is_elective
                )
                messages.success(request, f'Subject "{subject_name} ({code})" created successfully.')

        # Action 6: Assign Teacher & Subject to Class
        elif action == 'assign_class':
            class_id = request.POST.get('class_id')
            subject_id = request.POST.get('subject_id')
            teacher_id = request.POST.get('teacher_id')
            academic_year_id = request.POST.get('academic_year_id')

            classroom = Classroom.objects.get(id=class_id, school=school)
            subject = Subject.objects.get(id=subject_id, school=school)
            teacher = TeacherProfile.objects.get(id=teacher_id, school=school) if teacher_id else None

            if academic_year_id:
                academic_year = AcademicYear.objects.get(id=academic_year_id, school=school)
            else:
                academic_year = AcademicYear.objects.filter(school=school, is_current=True).first() or school.academic_years.first()

            if academic_year:
                SubjectAssignment.objects.update_or_create(
                    school=school,
                    academic_year=academic_year,
                    classroom=classroom,
                    subject=subject,
                    defaults={'teacher': teacher}
                )
                teacher_name = teacher.user.get_full_name() if teacher else "Unassigned"
                messages.success(request, f'Assigned {subject.name} in {classroom} to {teacher_name}.')
            else:
                messages.error(request, 'Please create an academic year first before assigning subjects.')

        return redirect('school_admin_dashboard')

    # Context Data
    academic_years = AcademicYear.objects.filter(school=school)
    grade_levels = GradeLevel.objects.filter(school=school)
    classrooms = Classroom.objects.filter(school=school).select_related('grade_level')
    subjects = Subject.objects.filter(school=school)
    teachers = TeacherProfile.objects.filter(school=school).select_related('user')
    students = StudentProfile.objects.filter(school=school).select_related('user')
    assignments = SubjectAssignment.objects.filter(school=school).select_related(
        'classroom__grade_level', 'subject', 'teacher__user', 'academic_year'
    )

    context = {
        'school': school,
        'academic_years': academic_years,
        'grade_levels': grade_levels,
        'classrooms': classrooms,
        'subjects': subjects,
        'teachers': teachers,
        'students': students,
        'assignments': assignments,
        'student_count': students.count(),
        'teacher_count': teachers.count(),
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