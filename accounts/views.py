from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_tenant_from_request
from .models import CustomUser, ParentProfile, StudentProfile, TeacherProfile
from .serializers import (
    CustomUserSerializer,
    ParentProfileSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer,
    TenantLoginSerializer,
)


def logout_view(request):
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user).delete()
        logout(request)
        messages.success(request, "You have been successfully logged out.")
    return redirect('login')


class TenantLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        school = get_tenant_from_request(request)
        return render(request, self.template_name, {"school": school})

    def post(self, request, *args, **kwargs):
        serializer = TenantLoginSerializer(
            data=request.data, context={"request": request}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            # Capture DRF validation errors and push to Django Messages for UI rendering
            for field, errors in e.detail.items():
                for error in errors:
                    messages.error(request, f"{error}")
            raise e

        user = serializer.validated_data["user"]
        school = serializer.validated_data.get("school")

        # Create Django Session so template views (@login_required) work properly
        login(request, user)

        # Success alert
        messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")

        # Generate REST token for API calls
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.get_full_name(),
                    "role": getattr(user, "role", None),
                },
                "school": (
                    {
                        "id": str(school.id),
                        "name": school.name,
                        "logo": school.logo.url if school.logo else None,
                        "primary_color": getattr(school, "primary_color", None),
                    }
                    if school
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return CustomUser.objects.all()
        school = getattr(user, "school", None)
        return CustomUser.objects.filter(school=school) if school else CustomUser.objects.none()


class TeacherProfileViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        school = getattr(self.request.user, "school", None)
        return TeacherProfile.objects.filter(school=school) if school else TeacherProfile.objects.none()


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        school = getattr(self.request.user, "school", None)
        return StudentProfile.objects.filter(school=school) if school else StudentProfile.objects.none()


class ParentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ParentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        school = getattr(self.request.user, "school", None)
        return ParentProfile.objects.filter(school=school) if school else ParentProfile.objects.none()