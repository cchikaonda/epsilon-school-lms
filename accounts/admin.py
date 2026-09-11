from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, TeacherProfile, StudentProfile, ParentProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'role', 'school', 'is_active', 'is_staff')
    list_filter = ('role', 'school', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'school__name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        ('Tenant & Role Settings', {'fields': ('school', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'school', 'password1', 'password2'),
        }),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'employee_id', 'joining_date')
    list_filter = ('school',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'employee_id')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'admission_number', 'gender', 'date_of_birth')
    list_filter = ('school', 'gender')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'admission_number')


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'occupation')
    list_filter = ('school',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    filter_horizontal = ('students',)