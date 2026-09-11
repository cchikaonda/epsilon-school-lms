import uuid
from django.db import models
from django.core.validators import FileExtensionValidator
from schools.models import School, AcademicYear, Term
from accounts.models import StudentProfile, ParentProfile, CustomUser
from academics.models import Classroom, SubjectAssignment


class StudentMedicalRecord(models.Model):
    """
    Tracks health-related information and medical emergency contacts for students.
    """
    class BloodGroup(models.TextChoices):
        A_PLUS = 'A+', 'A+'
        A_MINUS = 'A-', 'A-'
        B_PLUS = 'B+', 'B+'
        B_MINUS = 'B-', 'B-'
        O_PLUS = 'O+', 'O+'
        O_MINUS = 'O-', 'O-'
        AB_PLUS = 'AB+', 'AB+'
        AB_MINUS = 'AB-', 'AB-'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='medical_records')
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='medical_record')
    blood_group = models.CharField(max_length=10, choices=BloodGroup.choices, default=BloodGroup.UNKNOWN)
    allergies = models.TextField(blank=True, null=True, help_text="e.g., Peanuts, Penicillin")
    medical_conditions = models.TextField(blank=True, null=True, help_text="e.g., Asthma, Diabetes")
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=50)

    def __str__(self):
        return f"Medical Record: {self.student.user.get_full_name()}"


class ParentRelationship(models.Model):
    """
    Explicit M2M junction model mapping Parents to Students with specific relationship types.
    """
    class RelationshipType(models.TextChoices):
        FATHER = 'FATHER', 'Father'
        MOTHER = 'MOTHER', 'Mother'
        GUARDIAN = 'GUARDIAN', 'Guardian'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='parent_relationships')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='guardian_links')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='student_links')
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, default=RelationshipType.GUARDIAN)
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'parent')

    def save(self, *args, **kwargs):
        # Ensure only one primary contact per student per school
        if self.is_primary_contact:
            ParentRelationship.objects.filter(student=self.student, is_primary_contact=True).exclude(pk=self.pk).update(is_primary_contact=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent.user.get_full_name()} ({self.get_relationship_type_display()}) -> {self.student.user.get_full_name()}"


class Attendance(models.Model):
    """
    Tracks daily or session-based attendance records per student.
    """
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        EXCUSED = 'EXCUSED', 'Excused'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='recorded_attendances')

    class Meta:
        ordering = ['-date']
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.date} [{self.get_status_display()}]"


class StudentDocument(models.Model):
    """
    Stores uploaded files like birth certificates, transfer letters, and national IDs per student.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='student_documents')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=100, help_text="e.g., Birth Certificate, Previous Report Card")
    file = models.FileField(
        upload_to='student_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.student.user.get_full_name()}"


class IncidentReport(models.Model):
    """
    Logs disciplinary or commendable behavioral events for students.
    """
    class IncidentSeverity(models.TextChoices):
        LOW = 'LOW', 'Minor'
        MEDIUM = 'MEDIUM', 'Moderate'
        HIGH = 'HIGH', 'Severe'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='incident_reports')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='incidents')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='incidents')
    title = models.CharField(max_length=150)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=IncidentSeverity.choices, default=IncidentSeverity.LOW)
    action_taken = models.TextField(blank=True, null=True)
    reported_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='reported_incidents')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.student.user.get_full_name()} ({self.get_severity_display()})"