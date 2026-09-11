from django.contrib import admin
from .models import School, AcademicYear, Term, SchoolSetting


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


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'start_date', 'end_date', 'is_current')
    list_filter = ('school', 'is_current')
    search_fields = ('name', 'school__name')
    inlines = [TermInline]


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'school', 'start_date', 'end_date', 'is_current')
    list_filter = ('school', 'is_current')
    search_fields = ('name', 'school__name', 'academic_year__name')


@admin.register(SchoolSetting)
class SchoolSettingAdmin(admin.ModelAdmin):
    list_display = ('school', 'currency_code', 'currency_symbol', 'enable_sms_notifications', 'enable_online_payments')
    search_fields = ('school__name',)