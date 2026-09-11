import uuid
from django.db import models
from schools.models import School, AcademicYear
from accounts.models import TeacherProfile, StudentProfile


class GradeLevel(models.Model):
    """
    Represents educational levels/grades within a school (e.g., Form 1, Standard 8, Grade 10).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='grade_levels')
    name = models.CharField(max_length=50, help_text="e.g., Form 1, Standard 8")
    level_order = models.PositiveSmallIntegerField(help_text="Numeric order for sorting (e.g., 1, 2, 3)")

    class Meta:
        ordering = ['level_order', 'name']
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} ({self.school.name})"


class Classroom(models.Model):
    """
    Represents specific classes/streams (e.g., Form 1 East, Standard 8 Blue).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classrooms')
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name='classrooms')
    name = models.CharField(max_length=50, help_text="Stream name, e.g., 'East', 'Blue', or 'A'")
    class_teacher = models.ForeignKey(
        TeacherProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_classrooms'
    )
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        ordering = ['grade_level__level_order', 'name']
        unique_together = ('school', 'grade_level', 'name')

    def __str__(self):
        return f"{self.grade_level.name} {self.name}"


class Subject(models.Model):
    """
    Represents subjects taught at the school (e.g., Mathematics, Physical Science, Chichewa).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, help_text="e.g., MATH101, ENG01")
    is_elective = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        unique_together = ('school', 'code')

    def __str__(self):
        return f"{self.name} ({self.code})"


class SubjectAssignment(models.Model):
    """
    Links a Subject to a Classroom, Academic Year, and assigned Teacher.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subject_assignments')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='subject_assignments')
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='subject_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_assignments')
    teacher = models.ForeignKey(
        TeacherProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subject_assignments'
    )

    class Meta:
        unique_together = ('academic_year', 'classroom', 'subject')

    def __str__(self):
        teacher_name = self.teacher.user.get_full_name() if self.teacher else 'Unassigned'
        return f"{self.subject.name} - {self.classroom} ({teacher_name})"


class StudentEnrollment(models.Model):
    """
    Tracks a student's class enrollment per academic year.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='enrollments')
    roll_number = models.PositiveIntegerField(null=True, blank=True)
    enrolled_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'academic_year')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.classroom} ({self.academic_year.name})"


class TimetableSlot(models.Model):
    """
    Defines period allocations for class schedules.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='timetable_slots')
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE, related_name='timetable_slots')
    day = models.PositiveSmallIntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.get_day_display()} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}): {self.subject_assignment.subject.name}"