from rest_framework import serializers
from .models import (
    GradeLevel, 
    Classroom, 
    Subject, 
    SubjectAssignment, 
    StudentEnrollment, 
    TimetableSlot,
    Assessment,
    AssessmentSubmission
)


class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ['id', 'school', 'name', 'level_order']


class ClassroomSerializer(serializers.ModelSerializer):
    grade_level_name = serializers.ReadOnlyField(source='grade_level.name')

    class Meta:
        model = Classroom
        fields = ['id', 'school', 'grade_level', 'grade_level_name', 'name', 'class_teacher', 'capacity']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'school', 'name', 'code', 'is_elective']


class SubjectAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    classroom_name = serializers.ReadOnlyField(source='classroom.__str__')

    class Meta:
        model = SubjectAssignment
        fields = ['id', 'school', 'academic_year', 'classroom', 'classroom_name', 'subject', 'subject_name', 'teacher']


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.user.get_full_name')

    class Meta:
        model = StudentEnrollment
        fields = ['id', 'school', 'student', 'student_name', 'classroom', 'academic_year', 'roll_number', 'enrolled_at']


class TimetableSlotSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)

    class Meta:
        model = TimetableSlot
        fields = ['id', 'school', 'subject_assignment', 'day', 'day_display', 'start_time', 'end_time', 'room_number']


class AssessmentSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    subject_name = serializers.ReadOnlyField(source='subject_assignment.subject.name')
    classroom_name = serializers.ReadOnlyField(source='subject_assignment.classroom.__str__')
    created_by_name = serializers.ReadOnlyField(source='created_by.user.get_full_name')

    class Meta:
        model = Assessment
        fields = [
            'id', 
            'school', 
            'subject_assignment', 
            'subject_name', 
            'classroom_name', 
            'title', 
            'description', 
            'kind', 
            'kind_display', 
            'total_marks', 
            'due_date', 
            'quiz_data', 
            'created_by', 
            'created_by_name', 
            'created_at', 
            'updated_at'
        ]


class AssessmentSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.user.get_full_name')
    assessment_title = serializers.ReadOnlyField(source='assessment.title')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    graded_by_name = serializers.ReadOnlyField(source='graded_by.user.get_full_name')

    class Meta:
        model = AssessmentSubmission
        fields = [
            'id', 
            'school', 
            'assessment', 
            'assessment_title', 
            'student', 
            'student_name', 
            'content', 
            'file_attachment', 
            'score', 
            'feedback', 
            'status', 
            'status_display', 
            'submitted_at', 
            'graded_at', 
            'graded_by', 
            'graded_by_name'
        ]
        read_only_fields = ['submitted_at', 'graded_at', 'graded_by']