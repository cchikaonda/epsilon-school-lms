from django.db.models import Q, Value
from django.db.models.functions import Replace, Trim
from schools.models import School

def get_tenant_from_request(request):
    """
    Resolves the active School tenant strictly from request host headers.
    Supports exact custom domains, exact subdomains, hyphenated normalizations, 
    and plain development localhosts.
    """
    host = request.get_host().split(":")[0].lower().strip()

    # Base queryset with annotations for space-trimming and hyphen normalization
    base_queryset = School.objects.annotate(
        clean_subdomain=Trim('subdomain'),
        clean_custom_domain=Trim('custom_domain'),
        clean_code=Trim('code'),
        normalized_subdomain=Replace(Trim('subdomain'), Value('-'), Value('')),
        normalized_code=Replace(Trim('code'), Value('-'), Value(''))
    ).filter(is_active=True)

    # 1. Direct match on full custom domain or full subdomain header
    school = base_queryset.filter(
        Q(clean_custom_domain__iexact=host) | Q(clean_subdomain__iexact=host)
    ).first()

    # 2. Subdomain Prefix Extraction & Hyphen Normalization Match
    if not school:
        host_parts = host.split(".")
        if len(host_parts) >= 2 and host_parts[0] not in ["www", "localhost", "127"]:
            subdomain_prefix = host_parts[0].strip()
            normalized_prefix = subdomain_prefix.replace("-", "")

            school = base_queryset.filter(
                Q(clean_subdomain__iexact=subdomain_prefix) |
                Q(clean_code__iexact=subdomain_prefix) |
                Q(normalized_subdomain__iexact=normalized_prefix) |
                Q(normalized_code__iexact=normalized_prefix)
            ).first()

    # 3. Development Fallback ONLY for naked 'localhost' or '127.0.0.1'
    if not school and host in ["localhost", "127.0.0.1"]:
        school = base_queryset.first()

    return school