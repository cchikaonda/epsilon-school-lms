from django.contrib import admin
from .models import StudentMedicalRecord, ParentRelationship, Attendance, StudentDocument, IncidentReport


@admin.register(StudentMedicalRecord)
class StudentMedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'blood_group', 'emergency_contact_name', 'emergency_contact_phone', 'school')
    list_filter = ('school', 'blood_group')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'emergency_contact_name')


@admin.register(ParentRelationship)
class ParentRelationshipAdmin(admin.ModelAdmin):
    list_display = ('parent', 'student', 'relationship_type', 'is_primary_contact', 'school')
    list_filter = ('school', 'relationship_type', 'is_primary_contact')
    search_fields = ('parent__user__first_name', 'parent__user__last_name', 'student__user__first_name', 'student__user__last_name')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'date', 'status', 'school')
    list_filter = ('school', 'status', 'date', 'classroom')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'classroom__name')


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'uploaded_at', 'school')
    list_filter = ('school',)
    search_fields = ('title', 'student__user__first_name', 'student__user__last_name')


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'severity', 'term', 'reported_by', 'school', 'created_at')
    list_filter = ('school', 'severity', 'term')
    search_fields = ('title', 'student__user__first_name', 'student__user__last_name')