import uuid
from decimal import Decimal
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from schools.models import School, AcademicYear, Term
from accounts.models import TeacherProfile, StudentProfile
from django.core.validators import MinValueValidator, MaxValueValidator


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
    Tracks individual student registrations for specific subjects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subject_registrations')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='subject_registrations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_registrations')
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
    Defines categories of tests/assessments (e.g., Continuous Assessment vs End of Term Exam).
    """
    class Category(models.TextChoices):
        COURSEWORK = 'coursework', 'Continuous Assessment'
        EXAM = 'exam', 'End of Term Examination'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='assessment_types')
    name = models.CharField(max_length=100, help_text="e.g., Mid-Term Quiz, Assignment, Final Paper")
    category = models.CharField(
        max_length=20, 
        choices=Category.choices, 
        default=Category.COURSEWORK,
        help_text="Determines if this contributes to Continuous Assessment or End of Term weight pool"
    )
    weight_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Weight contribution towards its respective category pool",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        ordering = ['name']
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} ({self.get_category_display()} - {self.weight_percentage}%)"


class Assessment(models.Model):
    """
    Represents individual interactive tasks created by teachers, such as 
    Quizzes, Homework assignments, or Projects assigned to a specific subject classroom.
    """
    class AssessmentKind(models.TextChoices):
        QUIZ = 'QUIZ', 'Quiz'
        HOMEWORK = 'HOMEWORK', 'Homework'
        PROJECT = 'PROJECT', 'Project'
        OTHER = 'OTHER', 'Other Task'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='assessments')
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE, related_name='assessments')
    
    title = models.CharField(max_length=200, help_text="e.g., Chapter 3 Algebra Quiz")
    description = models.TextField(blank=True, null=True, help_text="Instructions or details for the students")
    kind = models.CharField(
        max_length=20, 
        choices=AssessmentKind.choices, 
        default=AssessmentKind.HOMEWORK,
        help_text="Type of student task (Quiz, Homework, Project)"
    )
    
    total_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Maximum achievable marks"
    )
    due_date = models.DateTimeField(help_text="Submission deadline")
    
    # Optional field if structured as online questions (e.g., JSON payload of quiz questions)
    quiz_data = models.JSONField(default=list, blank=True, null=True, help_text="Optional structural JSON for online quiz items")
    
    created_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_assessments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.title} - {self.subject_assignment.subject.name}"


class AssessmentSubmission(models.Model):
    """
    Tracks student submissions and grades for individual Assessments (Quizzes/Homework/Projects).
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        GRADED = 'GRADED', 'Graded'
        LATE = 'LATE', 'Submitted Late'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='assessment_submissions')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assessment_submissions')
    
    content = models.TextField(blank=True, null=True, help_text="Student text answer or submission notes")
    file_attachment = models.FileField(upload_to='assessment_submissions/', blank=True, null=True)
    
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Marks awarded for this submission"
    )
    feedback = models.TextField(blank=True, null=True, help_text="Teacher's comments/feedback")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_submissions')

    class Meta:
        unique_together = ('assessment', 'student')
        ordering = ['-submitted_at']

    def __str__(self):
        student_name = self.student.user.get_full_name()
        score_str = f"{self.score}/{self.assessment.total_marks}" if self.score is not None else "Ungraded"
        return f"{student_name} - {self.assessment.title} ({score_str})"


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
    Represents a formal examination period or reporting event (e.g., Term 1 End of Term Report).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exams')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='exams')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True, related_name='exams')
    name = models.CharField(max_length=150, help_text="e.g., End of Term 1 Examination")
    date = models.DateField(help_text="Date or start date of the exam")
    total_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Maximum possible marks for this report card score"
    )

    class Meta:
        ordering = ['-date']
        unique_together = ('school', 'academic_year', 'name')

    def __str__(self):
        term_str = f" - {self.term.name}" if self.term else ""
        return f"{self.name}{term_str} ({self.academic_year.name})"

    def compile_results_from_grades(self, classroom=None):
        """
        Aggregates GradeRecords, applies assessment weightings, merges continuous 
        assessment vs end of term percentages using classroom-configured weights 
        (e.g., 40% Continuous / 60% Exam), and upserts official ExamResults.
        """
        assignments = SubjectAssignment.objects.filter(
            school=self.school,
            academic_year=self.academic_year
        )
        if classroom:
            assignments = assignments.filter(classroom=classroom)

        for assignment in assignments:
            # Pull pre-configured weights for this classroom (e.g., 40 and 60)
            cw_total_weight = Decimal(str(assignment.classroom.get_coursework_weight())) / Decimal('100')
            ex_total_weight = Decimal(str(assignment.classroom.get_exam_weight())) / Decimal('100')

            # Fetch enrolled students
            students = StudentProfile.objects.filter(
                enrollments__classroom=assignment.classroom,
                enrollments__academic_year=self.academic_year
            ).distinct()

            for student in students:
                grades = GradeRecord.objects.filter(
                    subject_assignment=assignment,
                    student=student
                ).select_related('assessment_type')

                if not grades.exists():
                    continue

                cw_weighted_score = Decimal('0.00')
                cw_weight_sum = Decimal('0.00')

                ex_weighted_score = Decimal('0.00')
                ex_weight_sum = Decimal('0.00')

                for record in grades:
                    at_type = record.assessment_type
                    if record.max_score > 0:
                        percentage = (record.score / record.max_score) * Decimal('100')
                        weight = at_type.weight_percentage or Decimal('100.00')

                        if at_type.category == AssessmentType.Category.COURSEWORK:
                            cw_weighted_score += percentage * (weight / Decimal('100'))
                            cw_weight_sum += weight
                        elif at_type.category == AssessmentType.Category.EXAM:
                            ex_weighted_score += percentage * (weight / Decimal('100'))
                            ex_weight_sum += weight

                # Normalize continuous vs exam pools
                final_cw = (cw_weighted_score / (cw_weight_sum / Decimal('100'))) if cw_weight_sum > 0 else Decimal('0.00')
                final_ex = (ex_weighted_score / (ex_weight_sum / Decimal('100'))) if ex_weight_sum > 0 else Decimal('0.00')

                # Combine using the preset 40/60 split rule
                final_percentage = (final_cw * cw_total_weight) + (final_ex * ex_total_weight)
                actual_marks = (final_percentage / Decimal('100')) * self.total_marks

                # Upsert final report card record
                ExamResult.objects.update_or_create(
                    school=self.school,
                    exam=self,
                    student=student,
                    subject=assignment.subject,
                    defaults={
                        'marks_obtained': round(actual_marks, 2),
                        'remarks': 'Auto-compiled from Continuous & Exam assessments'
                    }
                )


class ExamResult(models.Model):
    """
    Stores a student's final compiled score and letter grade for a specific exam event and subject.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exam_results')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='exam_results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_results')
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Final compiled marks scored by the student"
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

    def save(self, *args, **kwargs):
        """
        Automatically computes and assigns the appropriate letter grade based on 
        the classroom or school grading scale whenever saved.
        """
        enrollment = self.student.enrollments.filter(academic_year=self.exam.academic_year).first()
        grading_scale = enrollment.classroom.get_grading_scale() if enrollment else self.school.settings.get_grading_scale()
        
        pct = float(self.percentage)
        assigned_grade = None
        
        if grading_scale:
            sorted_scale = sorted(grading_scale, key=lambda x: x.get('min', 0), reverse=True)
            for tier in sorted_scale:
                if pct >= tier.get('min', 0):
                    assigned_grade = tier.get('grade')
                    break
        
        if assigned_grade:
            self.grade = assigned_grade
            
        super().save(*args, **kwargs)


@receiver(post_save, sender=School)
def create_default_school_assessment_types(sender, instance, created, **kwargs):
    """
    Automatically creates standard Continuous Assessment and Examination types 
    whenever a new school is initialized in the database.
    """
    if created:
        AssessmentType.objects.get_or_create(
            school=instance,
            name='Continuous Assessment',
            defaults={
                'category': AssessmentType.Category.COURSEWORK,
                'weight_percentage': Decimal('100.00')
            }
        )
        AssessmentType.objects.get_or_create(
            school=instance,
            name='End of Term Examination',
            defaults={
                'category': AssessmentType.Category.EXAM,
                'weight_percentage': Decimal('100.00')
            }
        )

    import uuid
from django.db import models
from schools.models import School, AcademicYear
from accounts.models import TeacherProfile
from .models import SubjectAssignment, Classroom

class LearningResource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='learning_resources')
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE, related_name='resources', null=True, blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='resources', null=True, blank=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='learning_resources/')
    
    uploaded_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name='uploaded_resources')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.subject_assignment or self.classroom}"