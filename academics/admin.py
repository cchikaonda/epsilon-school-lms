from django.contrib import admin
from django.contrib import messages
from .models import (
    GradeLevel, 
    Classroom, 
    Subject, 
    SubjectAssignment, 
    StudentEnrollment, 
    StudentSubjectEnrollment, 
    TimetableSlot, 
    AssessmentType, 
    Assessment,
    AssessmentSubmission,
    GradeRecord, 
    Exam, 
    ExamResult,
    LearningResource,
)

@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'level_order')
    list_filter = ('school',)
    search_fields = ('name', 'school__name')


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'school', 'grade_level', 'name', 'class_teacher', 'capacity', 'pass_rate', 'coursework_weight', 'exam_weight')
    list_filter = ('school', 'grade_level')
    search_fields = ('name', 'grade_level__name', 'school__name')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'school', 'is_elective')
    list_filter = ('school', 'is_elective')
    search_fields = ('name', 'code', 'school__name')


@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('subject', 'classroom', 'teacher', 'academic_year', 'school')
    list_filter = ('school', 'academic_year', 'classroom')
    search_fields = ('subject__name', 'classroom__name', 'teacher__user__first_name', 'teacher__user__last_name')


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'academic_year', 'school', 'roll_number')
    list_filter = ('school', 'academic_year', 'classroom')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__admission_number')


@admin.register(StudentSubjectEnrollment)
class StudentSubjectEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'academic_year', 'school', 'is_active')
    list_filter = ('school', 'academic_year', 'is_active', 'subject')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'subject__name')


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('subject_assignment', 'day', 'start_time', 'end_time', 'room_number', 'school')
    list_filter = ('school', 'day')
    search_fields = ('subject_assignment__subject__name', 'subject_assignment__classroom__name')


@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'weight_percentage', 'school')
    list_filter = ('school', 'category')
    search_fields = ('name', 'school__name')


class AssessmentSubmissionInline(admin.TabularInline):
    model = AssessmentSubmission
    extra = 0
    readonly_fields = ('submitted_at', 'graded_at', 'graded_by')
    fields = ('student', 'status', 'score', 'feedback', 'file_attachment', 'submitted_at', 'graded_at')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject_assignment', 'kind', 'total_marks', 'due_date', 'school')
    list_filter = ('school', 'kind', 'due_date')
    search_fields = ('title', 'subject_assignment__subject__name', 'subject_assignment__classroom__name')
    inlines = [AssessmentSubmissionInline]


@admin.register(AssessmentSubmission)
class AssessmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'student', 'status', 'score', 'submitted_at', 'school')
    list_filter = ('school', 'status', 'assessment__kind')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'assessment__title')
    readonly_fields = ('submitted_at', 'graded_at')


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'school', 'subject_assignment', 'student', 'assessment_type', 'score', 'max_score', 'percentage', 'remarks')
    list_filter = ('school', 'assessment_type', 'subject_assignment__academic_year')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'subject_assignment__subject__name')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'term', 'academic_year', 'date', 'total_marks', 'school')
    list_filter = ('school', 'academic_year', 'term')
    search_fields = ('name',)
    actions = ['compile_exam_results_action']

    @admin.action(description="Compile / Update official Exam Results from Grade Records")
    def compile_exam_results_action(self, request, queryset):
        compiled_count = 0
        for exam in queryset:
            exam.compile_results_from_grades()
            compiled_count += 1
        self.message_user(
            request, 
            f"Successfully compiled report card results for {compiled_count} exam period(s).", 
            messages.SUCCESS
        )


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'subject', 'marks_obtained', 'grade', 'percentage', 'school')
    list_filter = ('school', 'exam', 'subject', 'grade')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'subject__name')

@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'subject_assignment', 'classroom', 'uploaded_by', 'created_at')
    list_filter = ('school', 'created_at', 'subject_assignment__subject')
    search_fields = ('title', 'description', 'uploaded_by__user__first_name', 'uploaded_by__user__last_name')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(school=request.user.school)
        return qs