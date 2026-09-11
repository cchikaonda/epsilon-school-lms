from rest_framework import serializers
from .models import GradeLevel, Classroom, Subject, SubjectAssignment, StudentEnrollment, TimetableSlot


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