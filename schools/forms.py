import uuid
from django import forms
from django.contrib.auth import get_user_model

from schools.models import School, SchoolSetting, AcademicYear, Term
from academics.models import GradeLevel, Classroom

User = get_user_model()


# ==========================================
# SYSTEM & USER MANAGEMENT FORMS
# ==========================================

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500'}),
            'code': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-emerald-600 focus:ring-emerald-500'}),
        }


class UserManagementForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
        required=False
    )

    class Meta:
        model = User
        fields = [
            User.USERNAME_FIELD,
            'email',
            'first_name',
            'last_name',
            'role',
            'school',
            'is_active',
            'is_staff',
            'is_superuser'
        ] if User.USERNAME_FIELD != 'email' else [
            'email',
            'first_name',
            'last_name',
            'role',
            'school',
            'is_active',
            'is_staff',
            'is_superuser'
        ]
        
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'role': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'school': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-emerald-600'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'rounded text-emerald-600'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'rounded text-emerald-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username_field = User.USERNAME_FIELD
        if username_field in self.fields:
            self.fields[username_field].widget.attrs.update({'class': 'w-full px-3 py-2 border rounded-lg'})

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ==========================================
# SCHOOL ADMIN SETTINGS & CALENDAR FORMS
# ==========================================
class SchoolProfileForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'logo', 'primary_color', 'secondary_color', 'email', 'phone_number', 'address', 'city', 'country']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-700 file:cursor-pointer cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2'
            }),
            'primary_color': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'h-11 w-full rounded-xl bg-slate-800 border border-slate-700 cursor-pointer p-1'
            }),
            'secondary_color': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'h-11 w-full rounded-xl bg-slate-800 border border-slate-700 cursor-pointer p-1'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
            'address': forms.Textarea(attrs={
                'rows': 2, 
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 border border-slate-700 text-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition'
            }),
        }

class SchoolSettingForm(forms.ModelForm):
    class Meta:
        model = SchoolSetting
        fields = ['currency_code', 'currency_symbol', 'enable_sms_notifications', 'enable_online_payments']
        widgets = {
            'currency_code': forms.TextInput(attrs={'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'enable_sms_notifications': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded bg-slate-800 border-slate-700 text-indigo-600'}),
            'enable_online_payments': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded bg-slate-800 border-slate-700 text-indigo-600'}),
        }


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. 2025/2026', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded bg-slate-800 border-slate-700 text-indigo-600'}),
        }


class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = ['academic_year', 'name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Term 1', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded bg-slate-800 border-slate-700 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=school)


class GradeLevelForm(forms.ModelForm):
    class Meta:
        model = GradeLevel
        fields = ['name', 'level_order']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Form 1', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'level_order': forms.NumberInput(attrs={'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
        }


class StreamForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['grade_level', 'name']
        widgets = {
            'grade_level': forms.Select(attrs={'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. East, Blue, or Alpha', 'class': 'w-full rounded-xl bg-slate-800 border-slate-700 text-white px-4 py-2.5'}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields['grade_level'].queryset = GradeLevel.objects.filter(school=school)