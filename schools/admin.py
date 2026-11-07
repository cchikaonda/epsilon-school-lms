# schools/admin.py
from django.contrib import admin
from .admin_site import school_admin_site
from .models import (
    School, 
    AcademicYear, 
    Term, 
    SchoolSetting, 
)
from accounts.models import (
    CustomUser,
    StudentProfile, 
    TeacherProfile, 
    SchoolAdminProfile
)

# ==========================================
# 1. MIXINS FOR TENANT ISOLATION & PERMISSIONS
# ==========================================
class FullAccessModelAdminMixin:
    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and (request.user.is_superuser or super().has_view_permission(request, obj))

    def has_add_permission(self, request):
        return request.user.is_authenticated and (request.user.is_superuser or super().has_add_permission(request))

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and (request.user.is_superuser or super().has_change_permission(request, obj))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and (request.user.is_superuser or super().has_delete_permission(request, obj))


class TenantScopedAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_authenticated and request.user.is_superuser:
            return qs  # Superuser sees everything across all schools
        
        if request.user.school and hasattr(qs.model, 'school'):
            return qs.filter(school=request.user.school)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not change and hasattr(obj, 'school'):
            obj.school = request.user.school
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser and request.user.school:
            if hasattr(db_field.related_model, 'school'):
                kwargs["queryset"] = db_field.related_model.objects.filter(school=request.user.school)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class GlobalAdminBase(FullAccessModelAdminMixin, TenantScopedAdminMixin, admin.ModelAdmin):
    pass


# ==========================================
# 2. GLOBAL MASTER ADMIN MODELS (Default site)
# ==========================================
class AcademicYearInline(admin.TabularInline):
    model = AcademicYear
    extra = 1

class TermInline(admin.TabularInline):
    model = Term
    extra = 1

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'subdomain', 'subscription_status', 'is_active', 'created_at')
    list_filter = ('subscription_status', 'is_active', 'country')
    search_fields = ('name', 'code', 'subdomain', 'custom_domain', 'email')
    prepopulated_fields = {'code': ('name',), 'subdomain': ('name',)}
    inlines = [AcademicYearInline]


# ==========================================
# 3. TENANT-SCOPED SCHOOL ADMIN MODELS 
# ==========================================

@admin.register(CustomUser, site=school_admin_site)
class CustomUserAdmin(GlobalAdminBase):
    list_display = ('email', 'first_name', 'last_name', 'role', 'school', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'school')
    search_fields = ('email', 'first_name', 'last_name', 'school__name')
    ordering = ('email',)


@admin.register(AcademicYear, site=school_admin_site)
class AcademicYearAdmin(GlobalAdminBase):
    list_display = ('name', 'school', 'start_date', 'end_date', 'is_current')
    list_filter = ('school', 'is_current')
    search_fields = ('name', 'school__name')
    inlines = [TermInline]


@admin.register(Term, site=school_admin_site)
class TermAdmin(GlobalAdminBase):
    list_display = ('name', 'academic_year', 'school', 'start_date', 'end_date', 'is_current')
    list_filter = ('school', 'is_current')
    search_fields = ('name', 'school__name', 'academic_year__name')


@admin.register(SchoolSetting, site=school_admin_site)
class SchoolSettingAdmin(GlobalAdminBase):
    list_display = ('school', 'currency_code', 'currency_symbol', 'enable_sms_notifications', 'enable_online_payments')
    search_fields = ('school__name',)


@admin.register(StudentProfile, site=school_admin_site)
class StudentProfileAdmin(GlobalAdminBase):
    list_display = ('user', 'school', 'admission_number', 'gender')
    list_filter = ('school', 'gender')
    search_fields = ('user__first_name', 'user__last_name', 'admission_number', 'school__name')


@admin.register(TeacherProfile, site=school_admin_site)
class TeacherProfileAdmin(GlobalAdminBase):
    list_display = ('user', 'school', 'employment_number', 'department')
    list_filter = ('school', 'department')
    search_fields = ('user__first_name', 'user__last_name', 'employment_number', 'school__name')


@admin.register(SchoolAdminProfile, site=school_admin_site)
class SchoolAdminProfileAdmin(GlobalAdminBase):
    list_display = ('user', 'school', 'employee_id')
    list_filter = ('school',)
    search_fields = ('user__first_name', 'user__last_name', 'employee_id', 'school__name')