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



    path('dashboard/system-admin/', views.system_admin_dashboard, name='system_admin_dashboard'),
    
    # Schools CRUD (Updated to uuid:pk)
    path('dashboard/system-admin/schools/', views.school_list_create_view, name='school_manage'),
    path('dashboard/system-admin/schools/<uuid:pk>/edit/', views.school_edit_view, name='school_edit'),
    path('dashboard/system-admin/schools/<uuid:pk>/delete/', views.school_delete_view, name='school_delete'),

    # Users CRUD (Use uuid or int depending on your CustomUser primary key type)
    path('dashboard/system-admin/users/', views.user_list_create_view, name='user_manage'),
    path('dashboard/system-admin/users/<uuid:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('dashboard/system-admin/users/<uuid:pk>/delete/', views.user_delete_view, name='user_delete'),


    # Public Tenant Info Endpoint
    path('api/domain-info/', views.SchoolDomainInfoView.as_view(), name='school_domain_info'),

    # API ViewSets
    path('api/', include(router.urls)),
]