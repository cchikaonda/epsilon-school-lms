from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Register DRF ViewSets
router = DefaultRouter()
router.register(r'schools', views.SchoolViewSet, basename='school')
router.register(r'academic-years', views.AcademicYearViewSet, basename='academicyear')
router.register(r'terms', views.TermViewSet, basename='term')
router.register(r'settings', views.SchoolSettingViewSet, basename='schoolsetting')

urlpatterns = [
    # Core Landing & Redirect
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Specific Dashboards
    path('dashboard/admin/', views.school_admin_dashboard, name='school_admin_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),

    # Public Tenant Info Endpoint
    path('api/domain-info/', views.SchoolDomainInfoView.as_view(), name='school_domain_info'),

    # API ViewSets
    path('api/', include(router.urls)),
]