import uuid
from django.db import models
from schools.models import School, AcademicYear, Term
from accounts.models import TeacherProfile, StudentProfile
from django.core.validators import MinValueValidator, MaxValueValidator  # <--- ADD THIS LINE


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

    # Optional Classroom-Level Overrides (Falls back to global school settings if null)
    pass_rate = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    coursework_weight = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    exam_weight = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grading_scale = models.JSONField(default=list, blank=True, null=True)

    def get_pass_rate(self):
        if self.pass_rate is not None:
            return self.pass_rate
        return self.school.settings.pass_rate

    def get_coursework_weight(self):
        if self.coursework_weight is not None:
            return self.coursework_weight
        return self.school.settings.coursework_weight

    def get_exam_weight(self):
        if self.exam_weight is not None:
            return self.exam_weight
        return self.school.settings.exam_weight

    def get_grading_scale(self):
        if self.grading_scale:
            return self.grading_scale
        return self.school.settings.get_grading_scale()

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


class StudentSubjectEnrollment(models.Model):
    """
    Tracks individual student registrations for specific subjects 
    (crucial for elective subjects where not all classroom students take the subject).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subject_registrations')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='subject_registrations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_registrations')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='subject_registrations')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'subject', 'academic_year')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name} ({self.academic_year.name})"

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


class AssessmentType(models.Model):
    """
    Defines categories of tests/assessments (e.g., End of Term Exam, Mid-Term Quiz, Assignment).
    """
    class Category(models.TextChoices):
        COURSEWORK = 'coursework', 'Coursework'
        EXAM = 'exam', 'Examination'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='assessment_types')
    name = models.CharField(max_length=100, help_text="e.g., Mid-Term Assessment, Term 1 Quiz")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.COURSEWORK)
    weight_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Weight contribution towards the final grade category",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        ordering = ['name']
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GradeRecord(models.Model):
    """
    Stores individual student marks for a specific subject assignment and assessment type.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='grade_records')
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE, related_name='grade_records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='grade_records')
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.CASCADE, related_name='grade_records')
    
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Marks obtained by the student"
    )
    max_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Maximum possible marks for this assessment"
    )
    remarks = models.TextField(blank=True, null=True)
    
    recorded_by = models.ForeignKey(
        TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_grades'
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subject_assignment', 'student', 'assessment_type')
        ordering = ['student__user__last_name']

    def __str__(self):
        student_name = self.student.user.get_full_name()
        return f"{student_name} - {self.subject_assignment.subject.name}: {self.score}/{self.max_score}"

    @property
    def percentage(self):
        if self.max_score > 0:
            return (self.score / self.max_score) * 100
        return 0.00

class Exam(models.Model):
    """
    Represents a formal examination period or test event (e.g., Term 1 End of Term Exam).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exams')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='exams')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=150, help_text="e.g., End of Term 1 Examination")
    date = models.DateField(help_text="Date or start date of the exam")
    total_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Maximum possible marks for this exam"
    )

    class Meta:
        ordering = ['-date']
        unique_together = ('school', 'academic_year', 'term', 'name')

    def __str__(self):
        return f"{self.name} - {self.term.name} ({self.academic_year.name})"


class ExamResult(models.Model):
    """
    Stores a student's final score and grade for a specific exam and subject.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exam_results')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='exam_results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_results')
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Marks scored by the student"
    )
    grade = models.CharField(max_length=5, blank=True, null=True, help_text="e.g., A, B, C, D, F")
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_exam_results')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'student', 'subject')
        ordering = ['student__user__last_name']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name}: {self.marks_obtained}/{self.exam.total_marks} ({self.grade or 'N/A'})"

    @property
    def percentage(self):
        if self.exam.total_marks > 0:
            return (self.marks_obtained / self.exam.total_marks) * 100
        return 0.00