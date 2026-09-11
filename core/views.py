from django.shortcuts import render
from .utils import get_tenant_from_request

def home(request):
    school = get_tenant_from_request(request)

    # Debug Logging
    host = request.get_host().split(":")[0].lower().strip()
    print(f"\n--- [DEBUG HOME VIEW] ---")
    print(f"Extracted Host: '{host}'")
    print(f"Final School Matched: {school}")
    print(f"---------------------------\n")

    return render(request, "core/index.html", {"school": school})


