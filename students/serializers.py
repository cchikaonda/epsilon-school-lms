from rest_framework import serializers
from .models import StudentMedicalRecord, ParentRelationship, Attendance, StudentDocument, IncidentReport


class StudentMedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMedicalRecord
        fields = [
            'id', 'school', 'student', 'blood_group', 'allergies', 
            'medical_conditions', 'emergency_contact_name', 
            'emergency_contact_phone', 'emergency_contact_relationship'
        ]


class ParentRelationshipSerializer(serializers.ModelSerializer):
    parent_name = serializers.ReadOnlyField(source='parent.user.get_full_name')
    student_name = serializers.ReadOnlyField(source='student.user.get_full_name')

    class Meta:
        model = ParentRelationship
        fields = ['id', 'school', 'student', 'student_name', 'parent', 'parent_name', 'relationship_type', 'is_primary_contact']


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.user.get_full_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'school', 'student', 'student_name', 'classroom', 'date', 'status', 'status_display', 'remarks', 'recorded_by']


class StudentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDocument
        fields = ['id', 'school', 'student', 'title', 'file', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class IncidentReportSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = IncidentReport
        fields = ['id', 'school', 'student', 'term', 'title', 'description', 'severity', 'severity_display', 'action_taken', 'reported_by', 'created_at']
        read_only_fields = ['created_at']