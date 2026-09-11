import uuid
from django.db import models
from django.utils.text import slugify


class School(models.Model):
    """
    Main Tenant Model: Represents an individual school using the system.
    """
    class SubscriptionStatus(models.TextChoices):
        TRIAL = 'TRIAL', 'Trial'
        ACTIVE = 'ACTIVE', 'Active'
        PAST_DUE = 'PAST_DUE', 'Past Due'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g., Kamuzu Academy")
    code = models.SlugField(max_length=100, unique=True, help_text="Unique identifier, e.g., kamuzu-academy")
    
    # Domain / Subdomain Routing
    subdomain = models.CharField(max_length=100, unique=True, help_text="e.g., kamuzu (for kamuzu.epsilonlms.com)")
    custom_domain = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="e.g., portal.kamuzuacademy.com")
    
    # School Metadata & Branding
    logo = models.ImageField(upload_to='school_logos/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#0f172a', help_text="Hex color code (e.g. #0f172a)")
    secondary_color = models.CharField(max_length=7, default='#047857', help_text="Hex color code (e.g. #047857)")
    
    # Contact & Address Details
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Malawi')
    
    # Tenant Status & Billing
    subscription_status = models.CharField(
        max_length=20, 
        choices=SubscriptionStatus.choices, 
        default=SubscriptionStatus.TRIAL
    )
    is_active = models.BooleanField(default=True, help_text="Uncheck to disable access for this tenant.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "School"
        verbose_name_plural = "Schools"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)
        if not self.subdomain:
            self.subdomain = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    """
    Defines the school year for each tenant (e.g., 2025/2026 Academic Year).
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='academic_years')
    name = models.CharField(max_length=100, help_text="e.g., 2025/2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        unique_together = ('school', 'name')

    def save(self, *args, **kwargs):
        # Ensure only one academic year is active per school at a time
        if self.is_current:
            AcademicYear.objects.filter(school=self.school, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Term(models.Model):
    """
    Defines terms or semesters within an Academic Year (e.g., Term 1, Term 2, Term 3).
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='terms')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=50, help_text="e.g., Term 1")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_date']
        unique_together = ('academic_year', 'name')

    def save(self, *args, **kwargs):
        # Ensure only one term is active per school at a time
        if self.is_current:
            Term.objects.filter(school=self.school, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school.name} - {self.academic_year.name} ({self.name})"


class SchoolSetting(models.Model):
    """
    Stores tenant-specific configurations (grading schemes, currency, features enabled).
    """
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='settings')
    currency_code = models.CharField(max_length=10, default='MWK')
    currency_symbol = models.CharField(max_length=5, default='MK')
    enable_sms_notifications = models.BooleanField(default=True)
    enable_online_payments = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Settings for {self.school.name}"