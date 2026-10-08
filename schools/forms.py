from django import forms
from django.contrib.auth import get_user_model
from schools.models import School
from accounts.models import StudentProfile, TeacherProfile, ParentProfile, SchoolAdminProfile

User = get_user_model()


class SchoolForm(forms.ModelForm):
    """Form for managing School tenant details."""
    class Meta:
        model = School
        fields = ['name', 'code', 'email', 'phone_number', 'website', 'address', 'motto', 'logo', 'timezone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'motto': forms.TextInput(attrs={'class': 'form-control'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SchoolProfileForm(forms.ModelForm):
    """Form for initial school tenant creation."""
    class Meta:
        model = School
        fields = ['name', 'code', 'email', 'phone_number', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Code (e.g. KAK)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@school.com'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Physical Address'}),
        }


class UserManagementForm(forms.ModelForm):
    """Form for creating or updating users at the system/school admin level."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'school', 'is_active', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'school': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for users to edit their own core personal account details."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }


class StudentProfileForm(forms.ModelForm):
    """Form for managing student-specific personal info (DOB, Gender, Guardian details)."""
    class Meta:
        model = StudentProfile
        fields = ['date_of_birth', 'gender', 'guardian_name', 'guardian_phone', 'address']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'guardian_name': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SchoolSettingForm(forms.Form):
    """Form configuration for general school policy options."""
    currency_code = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_rate = forms.DecimalField(max_digits=5, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    coursework_weight = forms.DecimalField(max_digits=5, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    exam_weight = forms.DecimalField(max_digits=5, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))


class AcademicYearForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    is_current = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class TermForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    academic_year = forms.ModelChoiceField(queryset=School.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    is_current = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        if school:
            from academics.models import AcademicYear
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=school)


class GradeLevelForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    level_order = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))


class StreamForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    grade_level = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))