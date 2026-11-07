# schools/admin_site.py
from django.contrib.admin import AdminSite

class TenantAdminSite(AdminSite):
    site_header = "School Administration Portal"
    
    def has_permission(self, request):
        # 1. Must be logged in, active, and staff
        if not request.user.is_authenticated or not request.user.is_active or not request.user.is_staff:
            return False
            
        # 2. Global platform superusers can access any tenant admin site seamlessly
        if request.user.is_superuser:
            return True
            
        # 3. Diagnostic logs to inspect why an admin might be blocked
        user_school = getattr(request.user, 'school', None)
        request_school = getattr(request, 'school', None)
        
        print(f"--- TENANT ADMIN AUTH CHECK ---")
        print(f"User: {request.user.email} | Role: {getattr(request.user, 'role', 'None')}")
        print(f"User's Assigned School: {user_school}")
        print(f"Request School (from Subdomain): {request_school}")

        # 4. School Admin check: Must be a SCHOOL_ADMIN and belong to the current requested school tenant
        if getattr(request.user, 'role', None) == 'SCHOOL_ADMIN':
            if request_school and user_school == request_school:
                return True
            else:
                print("-> DENIED: School mismatch or subdomain request_school is missing/None.")
                
        return False

# Instantiate the custom tenant-isolated admin site
school_admin_site = TenantAdminSite(name='school_admin')