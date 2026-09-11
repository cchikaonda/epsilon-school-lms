import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from schools.models import School


class CustomUserManager(BaseUserManager):
    """
    Custom user manager supporting email-based authentication and school-level filtering.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin (System)'
    SCHOOL_ADMIN = 'SCHOOL_ADMIN', 'School Admin'
    TEACHER = 'TEACHER', 'Teacher'
    STUDENT = 'STUDENT', 'Student'
    PARENT = 'PARENT', 'Parent'
    ACCOUNTANT = 'ACCOUNTANT', 'Accountant'


class CustomUser(AbstractUser):
    """
    Base User Model: Links directly to a School tenant.
    """
    username = None  # Using email as primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Multi-Tenant Isolation Key (Null for global Super Admins)
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        related_name='users', 
        null=True, 
        blank=True,
        help_text="Tenant association for data scoping."
    )
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    role = models.CharField(
        max_length=20, 
        choices=UserRole.choices, 
        default=UserRole.STUDENT
    )
    
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Overridden permission fields to prevent reverse accessor collisions with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['first_name', 'last_name']
        unique_together = ('school', 'email')

    def __str__(self):
        school_name = self.school.name if self.school else 'Platform Global'
        return f"{self.first_name} {self.last_name} ({self.get_role_display()}) - {school_name}"


class SchoolAdminProfile(models.Model):
    """
    Profile extension for school administrators.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='school_admin_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='admin_profiles')
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    office_extension = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('school', 'employee_id')

    def __str__(self):
        return f"School Admin: {self.user.get_full_name()}"


class TeacherProfile(models.Model):
    """
    Profile extension for faculty/teachers.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='teacher_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teacher_profiles')
    employee_id = models.CharField(max_length=50)
    qualification = models.CharField(max_length=255, blank=True, null=True)
    joining_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('school', 'employee_id')

    def __str__(self):
        return f"Teacher: {self.user.get_full_name()}"


class AccountantProfile(models.Model):
    """
    Profile extension for school accountants and finance officers.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='accountant_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='accountant_profiles')
    employee_id = models.CharField(max_length=50)
    designation = models.CharField(max_length=100, default='Bursar / Accountant')

    class Meta:
        unique_together = ('school', 'employee_id')

    def __str__(self):
        return f"Accountant: {self.user.get_full_name()}"


class StudentProfile(models.Model):
    """
    Profile extension for enrolled students.
    """
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='student_profiles')
    admission_number = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    address = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('school', 'admission_number')

    def __str__(self):
        return f"Student: {self.user.get_full_name()} ({self.admission_number})"


class ParentProfile(models.Model):
    """
    Profile extension for parents/guardians with links to multiple students.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='parent_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='parent_profiles')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    students = models.ManyToManyField(StudentProfile, related_name='parents', blank=True)

    def __str__(self):
        return f"Parent: {self.user.get_full_name()}"