from django.contrib import admin
from .models import GradeLevel, Classroom, Subject, SubjectAssignment, StudentEnrollment, TimetableSlot


@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'level_order')
    list_filter = ('school',)
    search_fields = ('name', 'school__name')


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'school', 'grade_level', 'name', 'class_teacher', 'capacity')
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


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('subject_assignment', 'day', 'start_time', 'end_time', 'room_number', 'school')
    list_filter = ('school', 'day')
    search_fields = ('subject_assignment__subject__name', 'subject_assignment__classroom__name')