from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Register DRF ViewSets
router = DefaultRouter()
router.register(r'schools', views.SchoolViewSet, basename='school')
router.register(r'academic-years', views.AcademicYearViewSet, basename='academicyear')
router.register(r'terms', views.TermViewSet, basename='term')
router.register(r'settings', views.SchoolSettingViewSet, basename='schoolsetting')
router.register(r'classes', views.ClassViewSet, basename='class')
router.register(r'subjects', views.SubjectViewSet, basename='subject')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'teachers', views.TeacherViewSet, basename='teacher')
router.register(r'parents', views.ParentViewSet, basename='parent')
router.register(r'facilities', views.FacilityViewSet, basename='facility')

urlpatterns = [
    # Core Landing & Redirect
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Specific Role Dashboards
    path('dashboard/admin/', views.school_admin_dashboard, name='school_admin_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/parent/', views.parent_dashboard, name='parent_dashboard'),
    path('dashboard/accountant/', views.accountant_dashboard, name='accountant_dashboard'),
    path('dashboard/system-admin/', views.system_admin_dashboard, name='system_admin_dashboard'),
    
    # System Admin - Schools CRUD
    path('dashboard/system-admin/schools/', views.school_list_create_view, name='school_manage'),
    path('dashboard/system-admin/schools/<uuid:pk>/edit/', views.school_edit_view, name='school_edit'),
    path('dashboard/system-admin/schools/<uuid:pk>/delete/', views.school_delete_view, name='school_delete'),

    # System Admin - Users CRUD
    path('dashboard/system-admin/users/', views.user_list_create_view, name='user_manage'),
    path('dashboard/system-admin/users/<uuid:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('dashboard/system-admin/users/<uuid:pk>/delete/', views.user_delete_view, name='user_delete'),

    # User Profile & Academic Pages
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('academics/results/', views.exam_results_view, name='exam_results'),
    path('academics/assignments/', views.assignments_list_view, name='assignments_list'),
    path('academics/attendance/', views.attendance_record_view, name='attendance_record'),

    # Public Tenant Info Endpoint
    path('api/domain-info/', views.SchoolDomainInfoView.as_view(), name='school_domain_info'),

    # DRF API ViewSets
    path('api/', include(router.urls)),
]