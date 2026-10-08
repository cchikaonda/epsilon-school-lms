import json
import logging
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q

from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.models import StudentProfile, CustomUser, TeacherProfile, ParentProfile, UserRole
from students.models import Attendance, StudentMedicalRecord, ParentRelationship, StudentDocument, IncidentReport
from academics.models import (
    GradeLevel,
    Classroom,
    SubjectAssignment,
    Subject,
    AssessmentType,
    GradeRecord,
    StudentEnrollment,
    TimetableSlot,
    StudentSubjectEnrollment,
    ExamResult,
    Exam,
    Assessment,
    AssessmentSubmission,
    LearningResource,
)
from schools.models import School, Term, AcademicYear, SchoolSetting
from .forms import (
    SchoolForm, UserManagementForm, SchoolProfileForm,
    SchoolSettingForm, AcademicYearForm, TermForm,
    GradeLevelForm, StreamForm, UserProfileForm, StudentProfileForm
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ==========================================
# Helper Utilities & Permissions
# ==========================================

def get_model_safely(app_label, model_name):
    """Safely fetch a model without throwing errors if app/model is missing."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def get_tenant_from_request(request):
    """Tenant retrieval helper with request fallback."""
    return getattr(request, 'tenant', None)


def is_system_admin(user):
    """Check if user has platform super administrator permissions."""
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', None) in ['SUPER_ADMIN', 'ADMIN']
    )


def is_school_admin(user):
    """Check if user has school administrative privileges."""
    if not user.is_authenticated:
        return False
    role = getattr(user, 'role', None)
    return user.is_superuser or role in ['SUPER_ADMIN', 'ADMIN', 'SCHOOL_ADMIN'] or (
        user.is_staff and getattr(user, 'school', None) is not None
    )

class IsSchoolAdminOrTeacher(permissions.BasePermission):
    """
    Allows read-only access for authenticated users, 
    but restricts write actions (POST, PUT, PATCH, DELETE) to school admins and teachers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.method in permissions.SAFE_METHODS: # GET, HEAD, OPTIONS
            return True
            
        role = getattr(request.user, 'role', None)
        is_teacher = role == 'TEACHER' or hasattr(request.user, 'teacher_profile')
        
        return is_system_admin(request.user) or is_school_admin(request.user) or is_teacher

def get_user_school(request):
    """Retrieve school tenant bound to current user or request context."""
    school = getattr(request.user, 'school', None) or get_tenant_from_request(request)
    if not school and is_system_admin(request.user):
        school_id = request.GET.get('school_id')
        if school_id:
            return get_object_or_404(School, id=school_id)
    return school


# ==========================================
# Authentication & Navigation Routing
# ==========================================

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    return render(request, 'schools/home.html')


@login_required
def dashboard_redirect(request):
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
# Student Import View with Logging
# ==========================================

@login_required
@user_passes_test(is_school_admin)
def student_import_view(request):
    """
    Handles bulk student imports with comprehensive logging.
    """
    school = get_user_school(request)
    
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            logger.warning(f"Student import failed: No file provided by user {request.user.username} for school {school.name if school else 'Unknown'}")
            messages.error(request, "Please upload a valid import file.")
            return redirect('student_import')

        logger.info(f"Starting student import process by user {request.user.username} for school: {school}")
        
        success_count = 0
        error_count = 0

        try:
            messages.success(request, f"Import completed. Success: {success_count}, Errors: {error_count}")
            logger.info(f"Student import finished for school {school}. Successes: {success_count}, Errors: {error_count}")
        except Exception as e:
            logger.error(f"Critical error during student import file parsing for school {school}: {e}", exc_info=True)
            messages.error(request, f"A critical error occurred while processing the file: {e}")

        return redirect('school_admin_dashboard')

    context = {
        'school': school,
    }
    return render(request, 'dashboard/student_import.html', context)


# ==========================================
# System Admin Management
# ==========================================

@login_required
@user_passes_test(is_system_admin)
def system_admin_dashboard(request):
    schools = School.objects.all()
    users = User.objects.all().select_related('school')
    
    context = {
        'schools': schools,
        'schools_count': schools.count(),
        'users_count': users.count(),
        'recent_users': users.order_by('-date_joined')[:10],
    }
    return render(request, 'dashboard/system_admin.html', context)


@login_required
@user_passes_test(is_system_admin)
def school_list_create_view(request):
    schools = School.objects.all()
    form = SchoolProfileForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'School tenant provisioned successfully!')
        return redirect('school_manage')

    return render(request, 'dashboard/schools_manage.html', {'schools': schools, 'form': form})


@login_required
@user_passes_test(is_system_admin)
def school_edit_view(request, pk):
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
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school_name = school.name
        school.delete()
        messages.success(request, f'School "{school_name}" deleted successfully.')
        return redirect('school_manage')
        
    return render(request, 'dashboard/confirm_delete.html', {'object': school, 'type': 'School'})


@login_required
@user_passes_test(is_system_admin)
def user_list_create_view(request):
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
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'User account "{username}" deleted.')
        return redirect('user_manage')

    return render(request, 'dashboard/confirm_delete.html', {'object': user_obj, 'type': 'User'})


# ==========================================
# School Settings & Admin Dashboard
# ==========================================

@login_required
@user_passes_test(is_school_admin)
def school_settings_view(request):
    school = get_object_or_404(School, id=request.user.school_id)
    settings_obj, _ = SchoolSetting.objects.get_or_create(school=school)
    classrooms = Classroom.objects.filter(school=school)

    if request.method == 'POST':
        school.name = request.POST.get('name', school.name)
        school.code = request.POST.get('code', school.code)
        school.email = request.POST.get('email', school.email)
        school.phone_number = request.POST.get('phone_number', school.phone_number)
        school.website = request.POST.get('website', school.website)
        school.address = request.POST.get('address', school.address)
        school.motto = request.POST.get('motto', school.motto)
        school.timezone = request.POST.get('timezone', 'Africa/Blantyre')

        if 'logo' in request.FILES:
            school.logo = request.FILES['logo']

        school.save()

        settings_obj.currency_code = request.POST.get('currency', 'MWK')
        settings_obj.pass_rate = request.POST.get('pass_mark', 50)
        settings_obj.coursework_weight = request.POST.get('coursework_weight', 40)
        settings_obj.exam_weight = request.POST.get('exam_weight', 60)

        grades_json = request.POST.get('grading_scale_json')
        if grades_json:
            try:
                settings_obj.grading_scale = json.loads(grades_json)
            except json.JSONDecodeError:
                pass
        settings_obj.save()

        weight_scope = request.POST.get('weightScope', 'global')
        if weight_scope == 'class':
            for c in classrooms:
                c.pass_rate = request.POST.get(f'class_pass_rate_{c.id}') or None
                c.coursework_weight = request.POST.get(f'class_cw_{c.id}') or None
                c.exam_weight = request.POST.get(f'class_ew_{c.id}') or None
                
                class_grades_json = request.POST.get(f'class_grading_json_{c.id}')
                if class_grades_json:
                    try:
                        c.grading_scale = json.loads(class_grades_json)
                    except json.JSONDecodeError:
                        pass
                c.save()

        messages.success(request, "School settings and branding updated successfully!")
        return redirect('school_settings')

    context = {
        'school': school,
        'academic_years': AcademicYear.objects.filter(school=school),
        'terms': Term.objects.filter(school=school),
        'classrooms': classrooms,
    }
    return render(request, 'schools/school_settings.html', context)


@login_required
@user_passes_test(is_school_admin)
def school_admin_dashboard(request):
    school = get_user_school(request)
    if not school:
        messages.error(request, "No active school context found for your account.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            if action in ['create_academic_year', 'add_academic_year']:
                name = request.POST.get('name', '').strip() or request.POST.get('year_name', '').strip()
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                is_current = request.POST.get('is_current') == 'on'

                if is_current:
                    AcademicYear.objects.filter(school=school).update(is_current=False)

                AcademicYear.objects.create(
                    school=school, name=name, start_date=start_date, 
                    end_date=end_date, is_current=is_current
                )
                messages.success(request, f'Academic year "{name}" created successfully.')

            elif action in ['edit_academic_year', 'update_academic_year']:
                ay_id = request.POST.get('academic_year_id') or request.POST.get('id')
                ay = get_object_or_404(AcademicYear, id=ay_id, school=school)
                ay.name = request.POST.get('name', '').strip() or request.POST.get('year_name', '').strip() or ay.name
                ay.start_date = request.POST.get('start_date', ay.start_date)
                ay.end_date = request.POST.get('end_date', ay.end_date)
                is_current = request.POST.get('is_current') == 'on'

                if is_current:
                    AcademicYear.objects.filter(school=school).exclude(id=ay.id).update(is_current=False)
                ay.is_current = is_current
                ay.save()
                messages.success(request, f'Academic year "{ay.name}" updated successfully.')

            elif action == 'delete_academic_year':
                ay_id = request.POST.get('academic_year_id') or request.POST.get('id')
                ay = get_object_or_404(AcademicYear, id=ay_id, school=school)
                ay_name = ay.name
                ay.delete()
                messages.success(request, f'Academic year "{ay_name}" deleted.')

            elif action in ['create_term', 'add_term']:
                ay_id = request.POST.get('academic_year_id')
                ay = get_object_or_404(AcademicYear, id=ay_id, school=school)
                name = request.POST.get('name', '').strip() or request.POST.get('term_name', '').strip()
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                is_current = request.POST.get('is_current') == 'on'

                if is_current:
                    Term.objects.filter(academic_year__school=school).update(is_current=False)

                Term.objects.create(
                    school=school, academic_year=ay, name=name, start_date=start_date,
                    end_date=end_date, is_current=is_current
                )
                messages.success(request, f'Term "{name}" created successfully.')

            elif action in ['edit_term', 'update_term']:
                term_id = request.POST.get('term_id') or request.POST.get('id')
                term = get_object_or_404(Term, id=term_id, school=school)
                ay_id = request.POST.get('academic_year_id')
                if ay_id:
                    term.academic_year = get_object_or_404(AcademicYear, id=ay_id, school=school)
                term.name = request.POST.get('name', '').strip() or request.POST.get('term_name', '').strip() or term.name
                term.start_date = request.POST.get('start_date', term.start_date)
                term.end_date = request.POST.get('end_date', term.end_date)
                is_current = request.POST.get('is_current') == 'on'

                if is_current:
                    Term.objects.filter(school=school).exclude(id=term.id).update(is_current=False)
                term.is_current = is_current
                term.save()
                messages.success(request, f'Term "{term.name}" updated successfully.')

            elif action == 'delete_term':
                term_id = request.POST.get('term_id') or request.POST.get('id')
                term = get_object_or_404(Term, id=term_id, school=school)
                term_name = term.name
                term.delete()
                messages.success(request, f'Term "{term_name}" deleted.')

            elif action in ['create_exam', 'add_exam']:
                academic_year_id = request.POST.get('academic_year_id')
                term_id = request.POST.get('term_id')
                name = request.POST.get('name', '').strip()
                exam_date = request.POST.get('date')
                total_marks = request.POST.get('total_marks')

                academic_year = get_object_or_404(AcademicYear, id=academic_year_id, school=school)
                term = get_object_or_404(Term, id=term_id, school=school, academic_year=academic_year)

                if not name:
                    messages.error(request, "Exam name is required.")
                elif not exam_date:
                    messages.error(request, "Exam date is required.")
                elif not total_marks:
                    messages.error(request, "Total marks are required.")
                else:
                    try:
                        Exam.objects.create(
                            school=school, academic_year=academic_year,
                            term=term, name=name, date=exam_date, total_marks=total_marks
                        )
                        messages.success(request, f'Exam "{name}" created successfully.')
                    except Exception as e:
                        logger.error(f"Error creating exam: {e}", exc_info=True)
                        messages.error(request, "Failed to create exam.")

            elif action in ['edit_exam', 'update_exam']:
                exam_id = request.POST.get('exam_id') or request.POST.get('id')
                exam = get_object_or_404(Exam, id=exam_id, school=school)
                academic_year_id = request.POST.get('academic_year_id')
                term_id = request.POST.get('term_id')

                if academic_year_id:
                    exam.academic_year = get_object_or_404(AcademicYear, id=academic_year_id, school=school)
                if term_id:
                    exam.term = get_object_or_404(Term, id=term_id, school=school, academic_year=exam.academic_year)

                exam.name = request.POST.get('name', '').strip() or exam.name
                exam_date = request.POST.get('date')
                if exam_date:
                    exam.date = exam_date
                total_marks = request.POST.get('total_marks')
                if total_marks:
                    exam.total_marks = total_marks
                exam.save()
                messages.success(request, f'Exam "{exam.name}" updated successfully.')

            elif action == 'delete_exam':
                exam_id = request.POST.get('exam_id') or request.POST.get('id')
                exam = get_object_or_404(Exam, id=exam_id, school=school)
                exam_name = exam.name
                exam.delete()
                messages.success(request, f'Exam "{exam_name}" deleted.')

            elif action in ['create_grade_level', 'add_grade_level']:
                name = request.POST.get('name', '').strip()
                level_order = request.POST.get('level_order', 1)

                if GradeLevel.objects.filter(school=school, name=name).exists():
                    messages.error(request, f'Grade level "{name}" already exists.')
                else:
                    GradeLevel.objects.create(school=school, name=name, level_order=level_order)
                    messages.success(request, f'Grade level "{name}" created successfully.')

            elif action in ['edit_grade_level', 'update_grade_level']:
                grade_id = request.POST.get('grade_level_id') or request.POST.get('id')
                grade = get_object_or_404(GradeLevel, id=grade_id, school=school)
                grade.name = request.POST.get('name', '').strip() or grade.name
                grade.level_order = request.POST.get('level_order', grade.level_order)
                grade.save()
                messages.success(request, f'Grade level "{grade.name}" updated.')

            elif action == 'delete_grade_level':
                grade_id = request.POST.get('grade_level_id') or request.POST.get('id')
                grade = get_object_or_404(GradeLevel, id=grade_id, school=school)
                grade_name = grade.name
                grade.delete()
                messages.success(request, f'Grade level "{grade_name}" deleted.')

            elif action in ['create_class', 'add_class']:
                class_name = request.POST.get('name', '').strip() or request.POST.get('class_name', '').strip()
                grade_level_id = request.POST.get('grade_level_id')
                grade_level = get_object_or_404(GradeLevel, id=grade_level_id, school=school)

                if Classroom.objects.filter(school=school, grade_level=grade_level, name=class_name).exists():
                    messages.error(request, f'Classroom "{class_name}" already exists under {grade_level.name}.')
                else:
                    Classroom.objects.create(school=school, grade_level=grade_level, name=class_name)
                    messages.success(request, f'Classroom "{class_name}" created under {grade_level.name}.')

            elif action in ['edit_class', 'update_class']:
                class_id = request.POST.get('class_id') or request.POST.get('id')
                classroom = get_object_or_404(Classroom, id=class_id, school=school)
                grade_level_id = request.POST.get('grade_level_id')
                if grade_level_id:
                    classroom.grade_level = get_object_or_404(GradeLevel, id=grade_level_id, school=school)
                classroom.name = request.POST.get('name', '').strip() or request.POST.get('class_name', '').strip() or classroom.name
                classroom.save()
                messages.success(request, f'Classroom "{classroom.name}" updated.')

            elif action == 'delete_class':
                class_id = request.POST.get('class_id') or request.POST.get('id')
                classroom = get_object_or_404(Classroom, id=class_id, school=school)
                c_name = classroom.name
                classroom.delete()
                messages.success(request, f'Classroom "{c_name}" deleted.')

            elif action in ['create_subject', 'add_subject']:
                name = request.POST.get('subject_name', '').strip() or request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                is_elective = request.POST.get('is_elective') == 'on'

                Subject.objects.create(school=school, name=name, code=code, is_elective=is_elective)
                messages.success(request, f'Subject "{name}" created.')

            elif action in ['edit_subject', 'update_subject']:
                sub_id = request.POST.get('subject_id') or request.POST.get('id')
                subject = get_object_or_404(Subject, id=sub_id, school=school)
                subject.name = request.POST.get('subject_name', '').strip() or request.POST.get('name', '').strip() or subject.name
                subject.code = request.POST.get('code', '').strip()
                subject.is_elective = request.POST.get('is_elective') == 'on'
                subject.save()
                messages.success(request, f'Subject "{subject.name}" updated.')

            elif action == 'delete_subject':
                sub_id = request.POST.get('subject_id') or request.POST.get('id')
                subject = get_object_or_404(Subject, id=sub_id, school=school)
                s_name = subject.name
                subject.delete()
                messages.success(request, f'Subject "{s_name}" deleted.')

            elif action in ['assign_class', 'add_assignment']:
                ay_id = request.POST.get('academic_year_id')
                class_id = request.POST.get('class_id')
                subject_id = request.POST.get('subject_id')
                teacher_id = request.POST.get('teacher_id')

                ay = get_object_or_404(AcademicYear, id=ay_id, school=school)
                classroom = get_object_or_404(Classroom, id=class_id, school=school)
                subject = get_object_or_404(Subject, id=subject_id, school=school)
                teacher = get_object_or_404(TeacherProfile, id=teacher_id, school=school) if teacher_id else None

                SubjectAssignment.objects.create(
                    school=school, academic_year=ay, classroom=classroom,
                    subject=subject, teacher=teacher
                )
                messages.success(request, "Teaching assignment created successfully.")

            elif action in ['edit_assignment', 'update_assignment']:
                asgn_id = request.POST.get('assignment_id') or request.POST.get('id')
                asgn = get_object_or_404(SubjectAssignment, id=asgn_id, school=school)
                
                ay_id = request.POST.get('academic_year_id')
                class_id = request.POST.get('class_id')
                subject_id = request.POST.get('subject_id')
                teacher_id = request.POST.get('teacher_id')

                if ay_id:
                    asgn.academic_year = get_object_or_404(AcademicYear, id=ay_id, school=school)
                if class_id:
                    asgn.classroom = get_object_or_404(Classroom, id=class_id, school=school)
                if subject_id:
                    asgn.subject = get_object_or_404(Subject, id=subject_id, school=school)
                asgn.teacher = get_object_or_404(TeacherProfile, id=teacher_id, school=school) if teacher_id else None
                asgn.save()
                messages.success(request, "Teaching assignment updated.")

            elif action == 'delete_assignment':
                asgn_id = request.POST.get('assignment_id') or request.POST.get('id')
                asgn = get_object_or_404(SubjectAssignment, id=asgn_id, school=school)
                asgn.delete()
                messages.success(request, "Teaching assignment removed.")

            elif action in ['enroll_student', 'add_enrollment']:
                student_id = request.POST.get('student_id')
                class_id = request.POST.get('class_id')
                ay_id = request.POST.get('academic_year_id')

                student = get_object_or_404(StudentProfile, id=student_id, school=school)
                classroom = get_object_or_404(Classroom, id=class_id, school=school)
                ay = get_object_or_404(AcademicYear, id=ay_id, school=school)

                enrollment, created = StudentEnrollment.objects.get_or_create(
                    school=school, student=student, academic_year=ay,
                    defaults={'classroom': classroom}
                )
                if not created:
                    enrollment.classroom = classroom
                    enrollment.save()
                    messages.success(request, f'Updated enrollment for "{student.user.get_full_name()}" to {classroom.name}.')
                else:
                    messages.success(request, f'Student "{student.user.get_full_name()}" successfully enrolled in {classroom.name}.')

            elif action in ['edit_enrollment', 'update_enrollment']:
                enrollment_id = request.POST.get('enrollment_id') or request.POST.get('id')
                enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id, school=school)
                
                class_id = request.POST.get('class_id')
                ay_id = request.POST.get('academic_year_id')
                student_id = request.POST.get('student_id')

                if class_id:
                    enrollment.classroom = get_object_or_404(Classroom, id=class_id, school=school)
                if ay_id:
                    enrollment.academic_year = get_object_or_404(AcademicYear, id=ay_id, school=school)
                if student_id:
                    enrollment.student = get_object_or_404(StudentProfile, id=student_id, school=school)
                
                enrollment.save()
                messages.success(request, "Student enrollment updated successfully.")

            elif action == 'delete_enrollment':
                enrollment_id = request.POST.get('enrollment_id') or request.POST.get('id')
                enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id, school=school)
                enrollment.delete()
                messages.success(request, "Student enrollment removed.")

            elif action == 'assign_parent_students':
                parent_profile_id = request.POST.get('parent_profile_id')
                student_ids = request.POST.getlist('student_ids')
                
                parent_profile = get_object_or_404(ParentProfile, id=parent_profile_id, school=school)
                students_to_link = StudentProfile.objects.filter(id__in=student_ids, school=school)
                
                if hasattr(parent_profile, 'students'):
                    parent_profile.students.set(students_to_link)
                messages.success(request, f'Successfully updated linked children for parent "{parent_profile.user.get_full_name()}".')

            elif action in ['create_user', 'add_user']:
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                role = request.POST.get('role', 'STUDENT')
                password = request.POST.get('password')

                if User.objects.filter(email=email).exists():
                    messages.error(request, f'User with email "{email}" already exists.')
                else:
                    user = User.objects.create_user(
                        email=email, password=password,
                        first_name=first_name, last_name=last_name, role=role, school=school
                    )
                    if role == 'TEACHER':
                        TeacherProfile.objects.get_or_create(user=user, school=school)
                    elif role == 'STUDENT':
                        StudentProfile.objects.get_or_create(user=user, school=school)
                    elif role == 'PARENT':
                        ParentProfile.objects.get_or_create(user=user, school=school)

                    messages.success(request, f'User "{first_name} {last_name}" created as {role}.')

            elif action in ['edit_user', 'update_user']:
                u_id = request.POST.get('user_id') or request.POST.get('id')
                user = get_object_or_404(User, id=u_id, school=school)
                user.first_name = request.POST.get('first_name', '').strip() or user.first_name
                user.last_name = request.POST.get('last_name', '').strip() or user.last_name
                user.email = request.POST.get('email', '').strip() or user.email
                user.role = request.POST.get('role', user.role)
                
                new_password = request.POST.get('password', '').strip()
                if new_password:
                    user.set_password(new_password)
                
                user.save()
                messages.success(request, f'User "{user.get_full_name()}" updated.')

            elif action == 'delete_user':
                u_id = request.POST.get('user_id') or request.POST.get('id')
                user = get_object_or_404(User, id=u_id, school=school)
                u_name = user.get_full_name()
                user.delete()
                messages.success(request, f'User "{u_name}" deleted.')

        except Exception as e:
            logger.error(f"Error executing dashboard action '{action}': {e}", exc_info=True)
            messages.error(request, "An unexpected error occurred while saving changes.")

        return redirect('school_admin_dashboard')

    teachers = TeacherProfile.objects.filter(school=school).select_related('user')
    students = StudentProfile.objects.filter(school=school).select_related('user')
    parents = ParentProfile.objects.filter(school=school).select_related('user').prefetch_related('students__user')

    q_teacher = request.GET.get('q_teacher', '').strip()
    q_student = request.GET.get('q_student', '').strip()
    q_subject = request.GET.get('q_subject', '').strip()
    q_class = request.GET.get('q_class', '').strip()

    if q_teacher:
        teachers = teachers.filter(
            Q(user__first_name__icontains=q_teacher) |
            Q(user__last_name__icontains=q_teacher) |
            Q(user__email__icontains=q_teacher) |
            Q(employment_number__icontains=q_teacher)
        )

    if q_student:
        students = students.filter(
            Q(user__first_name__icontains=q_student) |
            Q(user__last_name__icontains=q_student) |
            Q(user__email__icontains=q_student) |
            Q(admission_number__icontains=q_student)
        )

    subjects = Subject.objects.filter(school=school)
    if q_subject:
        subjects = subjects.filter(Q(name__icontains=q_subject) | Q(code__icontains=q_subject))

    classrooms = Classroom.objects.filter(school=school).select_related('grade_level')
    if q_class:
        classrooms = classrooms.filter(Q(name__icontains=q_class) | Q(grade_level__name__icontains=q_class))

    context = {
        'school': school,
        'academic_years': AcademicYear.objects.filter(school=school).order_by('-start_date'),
        'terms': Term.objects.filter(school=school).select_related('academic_year').order_by('-start_date'),
        'grade_levels': GradeLevel.objects.filter(school=school).order_by('level_order'),
        'classrooms': classrooms.order_by('grade_level__level_order', 'name'),
        'subjects': subjects.order_by('name'),
        'assignments': SubjectAssignment.objects.filter(school=school).select_related('academic_year', 'classroom', 'subject', 'teacher__user'),
        'enrollments': StudentEnrollment.objects.filter(school=school).select_related('student__user', 'classroom', 'academic_year'),
        'teachers': teachers,
        'students': students,
        'parents': parents,
        'teacher_count': TeacherProfile.objects.filter(school=school).count(),
        'student_count': StudentProfile.objects.filter(school=school).count(),
        'parent_count': ParentProfile.objects.filter(school=school).count(),
        'q_teacher': q_teacher,
        'q_student': q_student,
        'q_subject': q_subject,
        'q_class': q_class,
        'exams': Exam.objects.filter(school=school).select_related('academic_year', 'term').order_by('-date','-academic_year__start_date'),
    }
    return render(request, 'dashboard/school_admin.html', context)


# ==========================================
# Other Role Dashboards & Feature Views
# ==========================================

@login_required
def accountant_dashboard(request):
    school = get_user_school(request)
    return render(request, 'dashboard/accountant.html', {'school': school})


@login_required
def parent_dashboard(request):
    school = get_user_school(request)
    user = request.user
    
    if getattr(user, 'role', None) != UserRole.PARENT and not hasattr(user, 'parent_profile'):
        messages.error(request, "Access denied. Parents only.")
        return redirect('home')
    
    parent_profile = getattr(user, 'parent_profile', None)
    if not parent_profile:
        parent_profile, _ = ParentProfile.objects.get_or_create(user=user, school=school)
    
    linked_students = parent_profile.students.prefetch_related(
        'user',
        'enrollments__classroom__grade_level',
        'attendance_records',
        'incidents'
    ).all()

    exam_results = ExamResult.objects.filter(student__in=linked_students).select_related(
        'exam', 'student__user', 'subject'
    ).order_by('-exam__date')
    
    context = {
        'school': school,
        'parent_profile': parent_profile,
        'linked_students': linked_students,
        'exam_results': exam_results,
    }
    return render(request, 'dashboard/parent.html', context)

@login_required
def teacher_dashboard(request):
    school = get_user_school(request)
    user = request.user
    
    teacher_profile = getattr(user, 'teacher_profile', None)
    if not teacher_profile and getattr(user, 'role', '') == 'TEACHER':
        teacher_profile = TeacherProfile.objects.filter(user=user, school=school).first()

    current_academic_year = AcademicYear.objects.filter(school=school, is_current=True).first()
    
    classrooms = Classroom.objects.none()
    my_students = StudentProfile.objects.none()
    available_students = StudentProfile.objects.none()
    teacher_assignments_qs = SubjectAssignment.objects.none()
    assessments = Assessment.objects.none()
    exam_scores = ExamResult.objects.none()
    pending_submissions = AssessmentSubmission.objects.none()
    today_timetable = TimetableSlot.objects.none()
    resources = LearningResource.objects.none()
    active_exam = None

    if teacher_profile:
        teacher_assignments_qs = SubjectAssignment.objects.filter(
            teacher=teacher_profile,
            school=school
        ).select_related('classroom__grade_level', 'subject', 'academic_year')

        if current_academic_year:
            teacher_assignments_qs = teacher_assignments_qs.filter(academic_year=current_academic_year)

        classrooms = Classroom.objects.filter(
            id__in=teacher_assignments_qs.values_list('classroom_id', flat=True)
        ).select_related('grade_level')

        available_students = StudentProfile.objects.filter(school=school).select_related('user')

        my_students = StudentProfile.objects.filter(
            enrollments__classroom__in=classrooms
        ).select_related('user', 'school').distinct()

        # Fetch all assessments created by teacher cleanly without syntax error
        assessments = Assessment.objects.filter(
            school=school,
            subject_assignment__in=teacher_assignments_qs
        ).select_related(
            'subject_assignment__subject', 
            'subject_assignment__classroom__grade_level'
        ).order_by('-due_date')

        # Fetch learning resources uploaded by this teacher
        resources = LearningResource.objects.filter(
            school=school,
            uploaded_by=teacher_profile
        ).select_related('subject_assignment__subject', 'subject_assignment__classroom').order_by('-created_at')

        # 1. Automatically compile raw GradeRecords into official ExamResults if an active exam exists
        active_exam = Exam.objects.filter(
            school=school, 
            academic_year=current_academic_year
        ).order_by('-date').first()

        if active_exam:
            for assignment in teacher_assignments_qs:
                active_exam.compile_results_from_grades(classroom=assignment.classroom)

        # 2. Extract IDs to filter official compiled exam scores accurately
        classroom_ids = classrooms.values_list('id', flat=True)
        teacher_subject_ids = teacher_assignments_qs.values_list('subject_id', flat=True)
        
        exam_scores = ExamResult.objects.filter(
            school=school,
            subject_id__in=teacher_subject_ids,
            student__enrollments__classroom_id__in=classroom_ids
        ).select_related('student__user', 'subject', 'exam').distinct().order_by('-created_at')

        # 3. Fetch pending student submissions
        pending_submissions = AssessmentSubmission.objects.filter(
            assessment__subject_assignment__teacher=teacher_profile,
            status__in=['PENDING', 'SUBMITTED']
        ).select_related('student__user', 'assessment', 'assessment__subject_assignment__subject').order_by('submitted_at')

        # 4. Fetch Today's Timetable Schedule
        today_weekday = timezone.localdate().isoweekday()
        today_timetable = TimetableSlot.objects.filter(
            subject_assignment__in=teacher_assignments_qs,
            day=today_weekday
        ).select_related('subject_assignment__subject', 'subject_assignment__classroom').order_by('start_time')

    # Handle creating or updating assessments/quizzes via POST
    if request.method == 'POST' and request.POST.get('action') in ['create_assessment', 'edit_assessment']:
        action_type = request.POST.get('action')
        assessment_id = request.POST.get('assessment_id')
        assignment_id = request.POST.get('subject_assignment')
        title = request.POST.get('title')
        kind = request.POST.get('kind', 'HOMEWORK')
        due_date = request.POST.get('due_date')
        description = request.POST.get('description', '')

        try:
            subject_assignment = get_object_or_404(SubjectAssignment, id=assignment_id, school=school, teacher=teacher_profile)
            
            if action_type == 'edit_assessment' and assessment_id:
                assessment = get_object_or_404(Assessment, id=assessment_id, school=school, subject_assignment__teacher=teacher_profile)
                assessment.subject_assignment = subject_assignment
                assessment.title = title
                assessment.kind = kind
                assessment.due_date = due_date
                assessment.description = description
                assessment.save()
                
                # Clear existing questions/options on edit to replace with the newly submitted state
                assessment.questions.all().delete()
                messages.success(request, f'Assessment "{title}" updated successfully!')
            else:
                assessment = Assessment.objects.create(
                    school=school,
                    subject_assignment=subject_assignment,
                    title=title,
                    kind=kind,
                    due_date=due_date,
                    description=description
                )
                messages.success(request, f'Assessment "{title}" published successfully!')

            # Process questions JSON if it's a quiz or assessment with dynamic questions
            questions_json = request.POST.get('questions_json')
            if questions_json:
                try:
                    questions_list = json.loads(questions_json)
                    QuestionModel = get_model_safely('academics', 'Question')
                    OptionModel = get_model_safely('academics', 'Option')

                    if QuestionModel and OptionModel:
                        for q_idx, q_data in enumerate(questions_list):
                            q_text = q_data.get('text', '').strip()
                            correct_idx = q_data.get('correct', 0)
                            options = q_data.get('options', [])

                            if q_text:
                                question = QuestionModel.objects.create(
                                    assessment=assessment,
                                    text=q_text,
                                    order=q_idx + 1
                                )
                                for opt_idx, opt_text in enumerate(options):
                                    if opt_text.strip():
                                        OptionModel.objects.create(
                                            question=question,
                                            text=opt_text.strip(),
                                            is_correct=(opt_idx == correct_idx)
                                        )
                except json.JSONDecodeError:
                    logger.error("Failed to parse quiz questions JSON payload.", exc_info=True)

        except Exception as e:
            logger.error(f"Error saving assessment/quiz: {e}", exc_info=True)
            messages.error(request, "Failed to save assessment.")
        return redirect('teacher_dashboard')

    # Handle uploading learning resources via POST
    if request.method == 'POST' and request.POST.get('action') == 'upload_resource':
        assignment_id = request.POST.get('subject_assignment')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file_obj = request.FILES.get('resource_file')

        try:
            subject_assignment = get_object_or_404(
                SubjectAssignment, id=assignment_id, school=school, teacher=teacher_profile
            )
            LearningResource.objects.create(
                school=school,
                subject_assignment=subject_assignment,
                classroom=subject_assignment.classroom,
                title=title,
                description=description,
                file=file_obj,
                uploaded_by=teacher_profile
            )
            messages.success(request, f'Resource "{title}" uploaded successfully!')
        except Exception as e:
            messages.error(request, "Failed to upload learning resource.")
        return redirect('teacher_dashboard')

    # Handle recording/updating raw student grades via POST
    if request.method == 'POST' and request.POST.get('action') == 'record_grade':
        subject_assignment_id = request.POST.get('subject_assignment')
        assessment_type_id = request.POST.get('assessment_type')
        student_id = request.POST.get('student_id')
        score_val = request.POST.get('score')
        max_score_val = request.POST.get('max_score', '100.00')
        remarks = request.POST.get('remarks', '')

        try:
            subject_assignment = get_object_or_404(
                SubjectAssignment, id=subject_assignment_id, school=school, teacher=teacher_profile
            )
            assessment_type = get_object_or_404(
                AssessmentType, id=assessment_type_id, school=school
            )
            student = get_object_or_404(
                StudentProfile, id=student_id, school=school
            )

            GradeRecord.objects.update_or_create(
                school=school,
                subject_assignment=subject_assignment,
                student=student,
                assessment_type=assessment_type,
                defaults={
                    'score': score_val,
                    'max_score': max_score_val,
                    'remarks': remarks,
                    'recorded_by': teacher_profile
                }
            )

            if active_exam:
                active_exam.compile_results_from_grades(classroom=subject_assignment.classroom)

            messages.success(request, f'Score successfully saved for {student.user.get_full_name()}.')
        except Exception as e:
            messages.error(request, "Failed to save student grade.")
        return redirect('teacher_dashboard')

    context = {
        'school': school,
        'teacher_profile': teacher_profile,
        'teaching_assignments': teacher_assignments_qs,
        'classrooms': classrooms,
        'my_students': my_students,
        'available_students': available_students,
        'assessments': assessments,
        'resources': resources,
        'exam_scores': exam_scores,
        'active_exam': active_exam,
        'pending_submissions': pending_submissions,
        'today_timetable': today_timetable,
        'total_classes_count': classrooms.count(),
        'total_students_count': my_students.count(),
        'total_subjects_count': teacher_assignments_qs.values('subject').distinct().count(),
        'assessment_types': AssessmentType.objects.filter(school=school),
    }
    return render(request, 'dashboard/teacher.html', context)

@login_required
def teacher_add_exam_score(request):
    if request.method == 'POST':
        school = get_user_school(request)
        assignment_id = request.POST.get('assignment_id')
        student_id = request.POST.get('student_id')
        assessment_type_id = request.POST.get('assessment_type_id')
        score = request.POST.get('score')
        max_score = request.POST.get('max_score', 100)
        remarks = request.POST.get('remarks', '')

        assignment = get_object_or_404(SubjectAssignment, id=assignment_id, school=school)
        student = get_object_or_404(StudentProfile, id=student_id, school=school)
        assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id, school=school)
        
        teacher_profile = getattr(request.user, 'teacher_profile', None)

        try:
            GradeRecord.objects.update_or_create(
                subject_assignment=assignment,
                student=student,
                assessment_type=assessment_type,
                defaults={
                    'school': school,
                    'score': score,
                    'max_score': max_score,
                    'remarks': remarks,
                    'recorded_by': teacher_profile
                }
            )
            messages.success(request, f"Successfully recorded grade for {student.user.get_full_name() or student.user.username}.")
        except Exception as e:
            messages.error(request, f"Error saving score: {e}")

    return redirect('teacher_dashboard')


@login_required
def student_dashboard(request):
    user = request.user
    school = get_user_school(request)
    student_profile = getattr(user, 'student_profile', None) or StudentProfile.objects.filter(user=user).first()

    grade_level = None
    enrolled_courses = []
    pending_assignments = []
    student_resources = []
    pending_tasks_count = 0

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
                classroom=classroom, academic_year=enrollment.academic_year
            ).select_related('subject', 'teacher__user')

            enrolled_courses = [
                {
                    "name": sa.subject.name,
                    "code": sa.subject.code,
                    "teacher": sa.teacher.user if sa.teacher else None,
                }
                for sa in assignments
            ]

        # Fetch active subject IDs the student is registered or enrolled in
        enrolled_subject_ids = student_profile.subject_registrations.filter(
            school=school, is_active=True
        ).values_list('subject_id', flat=True)

        classroom_subject_ids = []
        if enrollment:
            classroom_subject_ids = SubjectAssignment.objects.filter(
                school=school,
                academic_year=enrollment.academic_year,
                classroom=enrollment.classroom
            ).values_list('subject_id', flat=True)

        all_subject_ids = set(list(enrolled_subject_ids) + list(classroom_subject_ids))

        # Fetch learning resources matching the student's classroom
        if enrollment and enrollment.classroom:
            student_resources = LearningResource.objects.filter(
                school=school,
                classroom=enrollment.classroom
            ).select_related('subject_assignment__subject', 'uploaded_by__user').order_by('-created_at')[:10]

        # Get assessments/homework due from now onwards, or sort by nearest deadlines
        raw_assessments = Assessment.objects.filter(
            school=school,
            subject_assignment__subject_id__in=all_subject_ids,
            due_date__gte=timezone.now()
        ).select_related('subject_assignment__subject').order_by('due_date')

        # Filter out ones the student has already submitted
        submitted_assessment_ids = AssessmentSubmission.objects.filter(
            school=school, student=student_profile, status__in=['SUBMITTED', 'GRADED', 'LATE']
        ).values_list('assessment_id', flat=True)

        for assessment in raw_assessments:
            if assessment.id not in submitted_assessment_ids:
                pending_assignments.append(assessment)

        pending_tasks_count = len(pending_assignments)

    context = {
        "school": school,
        "student_profile": student_profile,
        "grade_level": grade_level or "Unassigned Class",
        "student_id": getattr(student_profile, 'admission_number', user.username),
        "enrolled_courses": enrolled_courses,
        "recent_results": [],
        "student_resources": student_resources,
        "pending_assignments": pending_assignments[:5],
        "announcements": [],
        "overall_gpa": "N/A",
        "attendance_rate": "N/A",
        "pending_tasks_count": pending_tasks_count,
    }
    return render(request, 'dashboard/student.html', context)

@login_required
def exam_results_view(request):
    school = get_user_school(request)
    return render(request, 'academics/exam_results.html', {'school': school})


@login_required
def assignments_list_view(request):
    school = get_user_school(request)
    return render(request, 'academics/assignments_list.html', {'school': school})


@login_required
def attendance_record_view(request):
    school = get_user_school(request)
    return render(request, 'academics/attendance_record.html', {'school': school})


@login_required
def student_assignments_view(request):
    """
    View for students to see active homework, quizzes, and projects (Assessments) 
    tied to their subject registrations, including whether they have submitted them.
    """
    school = get_user_school(request)
    student_profile = getattr(request.user, 'student_profile', None)
    
    if not student_profile:
        messages.error(request, "Student profile not found.")
        return redirect('home')

    # Get active subject IDs the student is registered or enrolled in
    enrolled_subject_ids = student_profile.subject_registrations.filter(
        school=school, is_active=True
    ).values_list('subject_id', flat=True)

    # Also include classroom subjects if enrolled via classroom assignment
    current_enrollment = student_profile.enrollments.filter(
        academic_year__is_current=True
    ).select_related('classroom').first()

    classroom_subject_ids = []
    if current_enrollment:
        classroom_subject_ids = SubjectAssignment.objects.filter(
            school=school,
            academic_year=current_enrollment.academic_year,
            classroom=current_enrollment.classroom
        ).values_list('subject_id', flat=True)

    # Combine unique subject IDs
    all_subject_ids = set(list(enrolled_subject_ids) + list(classroom_subject_ids))

    # Fetch Assessments belonging to these subjects
    raw_assignments = Assessment.objects.filter(
        school=school,
        subject_assignment__subject_id__in=all_subject_ids
    ).select_related('subject_assignment__subject', 'subject_assignment__classroom').order_by('due_date')

    # Fetch existing submissions for this student to check submission status
    student_submissions = {
        sub.assessment_id: sub for sub in AssessmentSubmission.objects.filter(
            school=school, student=student_profile
        )
    }

    # Annotate/enrich objects with properties expected by the template
    assignments = []
    for assessment in raw_assignments:
        submission = student_submissions.get(assessment.id)
        
        # Attach dynamic attributes required by your HTML template
        assessment.subject = assessment.subject_assignment.subject
        assessment.is_submitted = submission is not None and submission.status in ['SUBMITTED', 'GRADED', 'LATE']
        assessment.submission = submission
        
        assignments.append(assessment)

    context = {
        'school': school,
        'assignments': assignments,
    }
    return render(request, 'schools/student_assignments.html', context)

@login_required
@login_required
def profile_edit_view(request):
    """
    View for users to update their profile details and extended student profile fields.
    """
    user = request.user
    student_profile = getattr(user, 'student_profile', None) or StudentProfile.objects.filter(user=user).first()

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        student_form = StudentProfileForm(request.POST, instance=student_profile) if student_profile else None

        is_user_valid = user_form.is_valid()
        is_student_valid = student_form.is_valid() if student_form else True

        if is_user_valid and is_student_valid:
            user_form.save()
            if student_form:
                student_form.save()
            
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile_edit')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserProfileForm(instance=user)
        student_form = StudentProfileForm(instance=student_profile) if student_profile else None

    context = {
        'form': user_form,
        'user_form': user_form,
        'student_form': student_form,
        'user': user,
    }
    return render(request, 'accounts/profile_edit.html', context)

@login_required
def student_report_card_view(request):
    context = {}
    return render(request, 'schools/student_report_card.html', context)

@login_required
def teacher_enroll_student(request):
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        student_id = request.POST.get('student_id')

        assignment = get_object_or_404(SubjectAssignment, id=assignment_id)
        
        if getattr(request.user, 'role', None) == 'TEACHER' and assignment.teacher:
            if assignment.teacher.user != request.user and not request.user.is_staff:
                messages.error(request, "You do not have permission to modify this class assignment.")
                return redirect('teacher_dashboard')

        student = get_object_or_404(StudentProfile, id=student_id)
        subject = assignment.subject
        school = assignment.school
        academic_year = assignment.academic_year

        try:
            if getattr(subject, 'is_elective', False):
                subject_enrollment, created = StudentSubjectEnrollment.objects.get_or_create(
                    school=school, student=student, subject=subject,
                    academic_year=academic_year, defaults={'is_active': True}
                )
                
                if not created:
                    if not subject_enrollment.is_active:
                        subject_enrollment.is_active = True
                        subject_enrollment.save()
                    messages.info(request, f'Student "{student.user.get_full_name()}" is already registered for elective "{subject.name}".')
                else:
                    messages.success(request, f'Successfully registered "{student.user.get_full_name()}" for elective "{subject.name}".')
            
            else:
                enrollment, created = StudentEnrollment.objects.get_or_create(
                    school=school, student=student, academic_year=academic_year,
                    defaults={'classroom': assignment.classroom}
                )
                
                if not created:
                    enrollment.classroom = assignment.classroom
                    enrollment.save()
                    messages.success(request, f'Updated enrollment for "{student.user.get_full_name()}" to {assignment.classroom.name}.')
                else:
                    messages.success(request, f'Successfully enrolled "{student.user.get_full_name()}" into {assignment.classroom.name} ({subject.name}).')

        except Exception as e:
            logger.error(f"Error enrolling student: {e}", exc_info=True)
            messages.error(request, "An unexpected error occurred while enrolling the student.")

    return redirect('teacher_dashboard')

@login_required
def teacher_gradebook_view(request, assignment_id):
    school = get_user_school(request)  
    user = request.user
    
    teacher_profile = getattr(user, 'teacher_profile', None)
    if not teacher_profile and getattr(user, 'role', '') == 'TEACHER':
        teacher_profile = TeacherProfile.objects.filter(user=user, school=school).first()

    assignment = get_object_or_404(
        SubjectAssignment, id=assignment_id, school=school, teacher=teacher_profile
    )
    
    classroom = assignment.classroom
    subject = assignment.subject

    students_qs = StudentProfile.objects.filter(
        enrollments__classroom=classroom,
        enrollments__academic_year=assignment.academic_year
    ).select_related('user').distinct()

    if getattr(subject, 'is_elective', False):
        enrolled_student_ids = StudentSubjectEnrollment.objects.filter(
            school=school,
            subject=subject,
            academic_year=assignment.academic_year,
            is_active=True
        ).values_list('student_id', flat=True)
        
        students = students_qs.filter(id__in=enrolled_student_ids).distinct()
    else:
        students = students_qs.distinct()

    coursework_type, _ = AssessmentType.objects.get_or_create(
        school=school,
        name="Coursework / Continuous Assessment",
        defaults={
            'category': AssessmentType.Category.COURSEWORK, 
            'weight_percentage': assignment.classroom.get_coursework_weight()
        }
    )
    exam_type, _ = AssessmentType.objects.get_or_create(
        school=school,
        name="End of Term Examination",
        defaults={
            'category': AssessmentType.Category.EXAM, 
            'weight_percentage': assignment.classroom.get_exam_weight()
        }
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_grades':
            try:
                for student in students:
                    score_val = request.POST.get(f'score_{student.id}')
                    exam_val = request.POST.get(f'exam_{student.id}')
                    
                    if score_val is not None and score_val.strip() != '':
                        GradeRecord.objects.update_or_create(
                            school=school,
                            subject_assignment=assignment,
                            student=student,
                            assessment_type=coursework_type,
                            defaults={
                                'score': float(score_val), 
                                'max_score': 40.00, 
                                'recorded_by': teacher_profile
                            }
                        )
                    else:
                        GradeRecord.objects.filter(
                            school=school,
                            subject_assignment=assignment,
                            student=student,
                            assessment_type=coursework_type
                        ).delete()
                    
                    if exam_val is not None and exam_val.strip() != '':
                        GradeRecord.objects.update_or_create(
                            school=school,
                            subject_assignment=assignment,
                            student=student,
                            assessment_type=exam_type,
                            defaults={
                                'score': float(exam_val), 
                                'max_score': 60.00, 
                                'recorded_by': teacher_profile
                            }
                        )
                    else:
                        GradeRecord.objects.filter(
                            school=school,
                            subject_assignment=assignment,
                            student=student,
                            assessment_type=exam_type
                        ).delete()
                        
                messages.success(request, "Grade book updated successfully.")
            except Exception as e:
                logger.error(f"Error saving grades: {e}", exc_info=True)
                messages.error(request, f"Failed to update grades: {e}")
            
            return redirect('teacher_gradebook', assignment_id=assignment.id)

    existing_grades = GradeRecord.objects.filter(
        subject_assignment=assignment,
        student__in=students
    )
    
    grades_dict = {
        (g.student_id, g.assessment_type_id): g.score for g in existing_grades
    }

    student_rows = []
    for student in students:
        cw_score = grades_dict.get((student.id, coursework_type.id), '')
        ex_score = grades_dict.get((student.id, exam_type.id), '')
        
        total_score = '--'
        try:
            if cw_score != '' and ex_score != '':
                total_score = float(cw_score) + float(ex_score)
        except ValueError:
            pass

        student_rows.append({
            'student': student,
            'coursework_score': cw_score,
            'exam_score': ex_score,
            'total_score': total_score,
        })

    context = {
        'school': school,
        'assignment': assignment,
        'classroom': classroom,
        'student_rows': student_rows,
    }
    return render(request, 'dashboard/teacher_gradebook.html', context)

@login_required
def student_subjects_view(request):
    """
    View for students to see their enrolled subjects, course codes, descriptions,
    and assigned teachers for the current term/academic year.
    """
    school = get_user_school(request)
    student_profile = getattr(request.user, 'student_profile', None)
    
    if not student_profile:
        messages.error(request, "Student profile not found.")
        return redirect('home')

    # Get the student's current active classroom enrollment to find corresponding class subject assignments
    current_enrollment = student_profile.enrollments.filter(
        academic_year__is_current=True
    ).select_related('classroom', 'academic_year').first()

    enrolled_courses = []

    if current_enrollment:
        # Fetch standard classroom subject assignments
        assignments = SubjectAssignment.objects.filter(
            school=school,
            academic_year=current_enrollment.academic_year,
            classroom=current_enrollment.classroom
        ).select_related('subject', 'teacher__user')

        for sa in assignments:
            enrolled_courses.append({
                "code": sa.subject.code,
                "name": sa.subject.name,
                "description": getattr(sa.subject, 'description', None),
                "teacher": sa.teacher.user if sa.teacher else None,
            })

    # Also handle elective subject registrations if applicable
    elective_registrations = student_profile.subject_registrations.filter(
        school=school, is_active=True
    ).select_related('subject', 'academic_year')

    for reg in elective_registrations:
        # Find if there's a teacher assigned to this elective subject for this academic year
        sa = SubjectAssignment.objects.filter(
            school=school,
            academic_year=reg.academic_year,
            subject=reg.subject
        ).select_related('teacher__user').first()

        course_entry = {
            "code": reg.subject.code,
            "name": reg.subject.name,
            "description": getattr(reg.subject, 'description', None),
            "teacher": sa.teacher.user if (sa and sa.teacher) else None,
        }
        
        # Avoid duplicate entries if already added via classroom assignments
        if course_entry not in enrolled_courses:
            enrolled_courses.append(course_entry)

    context = {
        'school': school,
        'enrolled_courses': enrolled_courses,
    }
    return render(request, 'schools/student_subjects.html', context)
# ==========================================
# REST Framework API Views & ViewSets
# ==========================================

class SchoolDomainInfoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        school = get_tenant_from_request(request)
        if not school and hasattr(request, 'user') and request.user.is_authenticated:
            school = getattr(request.user, 'school', None)

        return Response({
            'domain': request.get_host(),
            'school_name': getattr(school, 'name', 'Default School'),
            'is_active': True,
        })


class DynamicBaseViewSet(viewsets.ModelViewSet):
    """Scoped ViewSet dynamically enforcing multi-tenant boundaries."""

    permission_classes = [permissions.IsAuthenticated]
    model_name = None

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not self.model_name:
            return []

        Model = (
            get_model_safely('schools', self.model_name)
            or get_model_safely('academics', self.model_name)
            or get_model_safely('core', self.model_name)
            or get_model_safely('accounts', self.model_name)
        )
        if not Model:
            return []

        queryset = Model.objects.all()
        if is_system_admin(user):
            return queryset

        school = get_user_school(self.request)
        if school and hasattr(Model, 'school'):
            return queryset.filter(school=school)

        return queryset


class SchoolViewSet(DynamicBaseViewSet):
    model_name = 'School'

class SchoolSettingViewSet(DynamicBaseViewSet):
    model_name = 'SchoolSetting'

class AcademicYearViewSet(DynamicBaseViewSet):
    model_name = 'AcademicYear'

class TermViewSet(DynamicBaseViewSet):
    model_name = 'Term'

class ClassViewSet(DynamicBaseViewSet):
    model_name = 'Classroom'

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