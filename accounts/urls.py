# accounts/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ParentProfileViewSet,
    StudentProfileViewSet,
    TeacherProfileViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"teachers", TeacherProfileViewSet, basename="teacher")
router.register(r"students", StudentProfileViewSet, basename="student")
router.register(r"parents", ParentProfileViewSet, basename="parent")

urlpatterns = [
    path("", include(router.urls)),

    
    
]