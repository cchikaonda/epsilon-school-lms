from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.shortcuts import render
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


def get_full_origin(request):
    """Helper to reconstruct full scheme + host + port (e.g. http://cognisphere.localhost:8000)"""
    scheme = request.scheme
    # HTTP_HOST includes port number if present (e.g., 'subdomain.domain.com:8000')
    host = request.META.get('HTTP_HOST') or request.get_host()
    return f"{scheme}://{host}"


def logout_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user).delete()
        logout(request)
        messages.success(request, "You have been successfully logged out.")
    
    origin = get_full_origin(request)

    if next_url:
        if next_url.startswith('http'):
            return HttpResponseRedirect(next_url)
        return HttpResponseRedirect(f"{origin}{next_url}")
        
    return HttpResponseRedirect(f"{origin}/login/")


class TenantLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        school = get_tenant_from_request(request)
        next_url = request.GET.get("next", "")
        return render(request, self.template_name, {"school": school, "next": next_url})

    def post(self, request, *args, **kwargs):
        serializer = TenantLoginSerializer(
            data=request.data, context={"request": request}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            for field, errors in e.detail.items():
                for error in errors:
                    messages.error(request, f"{error}")
            raise e

        user = serializer.validated_data["user"]
        school = serializer.validated_data.get("school")

        # Create Django Session so template views work properly
        login(request, user)

        # Success alert
        messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")

        # Generate REST token for API calls
        token, _ = Token.objects.get_or_create(user=user)

        # Reconstruct full origin (scheme + host + port)
        origin = get_full_origin(request)
        next_url = request.GET.get("next") or request.data.get("next")

        if next_url:
            target_url = next_url if next_url.startswith("http") else f"{origin}{next_url}"
        else:
            target_url = f"{origin}/dashboard/"

        # If submitted via normal HTML form, force hard browser redirect to absolute URL
        if request.content_type == "application/x-www-form-urlencoded":
            return HttpResponseRedirect(target_url)

        # Standard API Response with full redirect_url payload
        return Response(
            {
                "token": token.key,
                "redirect_url": target_url,
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