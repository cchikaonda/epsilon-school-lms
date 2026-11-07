# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from schools.models import School

class TenantMiddleware(MiddlewareMixin):
    """
    Identifies the current tenant school based on subdomain or custom domain 
    and attaches it to the request object.
    """
    def process_request(self, request):
        host = request.get_host().split(':')[0]  # Remove port if present
        parts = host.split('.')
        
        # Check subdomains (e.g., cognisphere.epsilonlms.tech or kakuleacademy.localhost)
        subdomain = None
        if len(parts) > 2 or (len(parts) == 2 and 'localhost' in parts[1]):
            subdomain = parts[0]
            
        school = None
        if subdomain and subdomain not in ['www', '127', 'localhost']:
            school = School.objects.filter(subdomain__iexact=subdomain, is_active=True).first()
        
        if not school:
            # Fallback check for exact custom domain match
            school = School.objects.filter(custom_domain__iexact=host, is_active=True).first()
            
        request.school = school