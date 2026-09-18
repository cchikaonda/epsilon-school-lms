from django import forms
from django.contrib.auth import get_user_model
from schools.models import School

User = get_user_model()

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
        # Dynamically fetch the primary identifier field (e.g., 'email' or 'username')
        # alongside first_name, last_name, role, and status flags
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
        # Apply standard styling to the dynamically generated USERNAME_FIELD
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