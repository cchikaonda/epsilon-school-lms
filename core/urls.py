from accounts.views import TenantLoginView, logout_view
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import home
from schools.views import (
    dashboard_redirect,
    school_admin_dashboard,
    student_dashboard,
    teacher_dashboard,
    student_dashboard,
    profile_edit_view,
    exam_results_view,
    assignments_list_view,
    attendance_record_view,
)

urlpatterns = [
    # Top-Level Web Pages
    path("", home, name="home"),
    path('admin/', admin.site.urls),
    path('login/', TenantLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/login/', TenantLoginView.as_view()),  # Fallback for default Django redirects

    # Dashboards
    path('dashboard/', dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/admin/', school_admin_dashboard, name='school_admin_dashboard'),
    path('dashboard/teacher/', teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', student_dashboard, name='student_dashboard'),

    # REST API Routes
    path('api-auth/', include('rest_framework.urls')),
    path('api/schools/', include('schools.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/students/', include('students.urls')),

    path('profile/edit/', profile_edit_view, name='profile_edit'),
    path('exams/results/', exam_results_view, name='exam_results'),
    path('assignments/', assignments_list_view, name='assignments_list'),
    path('attendance/', attendance_record_view, name='attendance_record'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)