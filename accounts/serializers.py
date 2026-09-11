from django.contrib.auth import authenticate
from rest_framework import serializers

from core.utils import get_tenant_from_request
from schools.models import School
from .models import CustomUser, ParentProfile, StudentProfile, TeacherProfile


class TenantLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        request = self.context.get("request")

        # 1. Resolve school tenant
        school = get_tenant_from_request(request) if request else None

        if not school and request:
            host = request.get_host().split(":")[0].lower().strip()
            subdomain_prefix = host.split(".")[0]

            school = School.objects.filter(custom_domain__iexact=host, is_active=True).first()
            if not school:
                school = School.objects.filter(subdomain__iexact=subdomain_prefix, is_active=True).first()
            if not school and host in ["localhost", "127.0.0.1"]:
                school = School.objects.filter(is_active=True).first()

        # 2. Authenticate credentials
        user = authenticate(request=request, username=email, password=password)
        if not user:
            raise serializers.ValidationError("Unable to log in with provided credentials.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        # 3. Verify user belongs to requested school portal
        if school and not user.is_superuser:
            user_school = getattr(user, "school", None)
            if user_school and user_school != school:
                raise serializers.ValidationError(
                    f"Access denied. Your account is not registered under {school.name}."
                )

        attrs["user"] = user
        attrs["school"] = school or getattr(user, "school", None)
        return attrs


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'password', 'first_name', 'last_name', 'phone_number', 
            'role', 'school', 'profile_picture', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'user_id', 'school', 'employee_id', 'qualification', 'joining_date']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = StudentProfile
        fields = ['id', 'user', 'user_id', 'school', 'admission_number', 'date_of_birth', 'gender', 'address']


class ParentProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )
    students = StudentProfileSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProfile
        fields = ['id', 'user', 'user_id', 'school', 'occupation', 'students']