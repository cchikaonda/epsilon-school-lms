from rest_framework import serializers
from .models import School, AcademicYear, Term, SchoolSetting


class SchoolSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolSetting
        fields = ['id', 'currency_code', 'currency_symbol', 'enable_sms_notifications', 'enable_online_payments']


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ['id', 'school', 'academic_year', 'name', 'start_date', 'end_date', 'is_current']
        read_only_fields = ['id']


class AcademicYearSerializer(serializers.ModelSerializer):
    terms = TermSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicYear
        fields = ['id', 'school', 'name', 'start_date', 'end_date', 'is_current', 'terms']
        read_only_fields = ['id']


class SchoolSerializer(serializers.ModelSerializer):
    settings = SchoolSettingSerializer(read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'name', 'code', 'subdomain', 'custom_domain', 'logo', 
            'primary_color', 'secondary_color', 'email', 'phone_number', 
            'address', 'city', 'country', 'subscription_status', 'is_active', 
            'created_at', 'settings'
        ]
        read_only_fields = ['id', 'created_at']