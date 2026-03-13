import httpx
from django.shortcuts import render

FASTAPI_URL = "http://127.0.0.1:8001"

def home(request):
    results = []
    query = ""
    error = None

    if request.method == "POST":
        query = request.POST.get("query", "")
        try:
            response = httpx.post(
                f"{FASTAPI_URL}/api/discover",
                json={"query": query},
                timeout=10.0
            )
            data = response.json()
            results = data.get("results", [])
        except Exception as e:
            error = "Could not connect to KhauBot backend. Is it running?"

    return render(request, "core/home.html", {
        "results": results,
        "query": query,
        "error": error,
    })


def vendor_register(request):
    success = False
    error = None

    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "category": request.POST.get("category"),
            "area": request.POST.get("area"),
            "address": request.POST.get("address"),
            "cuisine": request.POST.get("cuisine"),
            "signature_dishes": request.POST.get("signature_dishes"),
            "price_min": int(request.POST.get("price_min", 0)),
            "price_max": int(request.POST.get("price_max", 0)),
            "operating_hours": request.POST.get("operating_hours"),
            "open_days": request.POST.get("open_days"),
            "contact": request.POST.get("contact"),
            "whatsapp_link": request.POST.get("whatsapp_link", ""),
            "photo_url": request.POST.get("photo_url", ""),
        }
        try:
            response = httpx.post(
                f"{FASTAPI_URL}/api/vendor/register",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 201:
                success = True
            else:
                error = "Registration failed. Please try again."
        except Exception:
            error = "Could not connect to backend."

    return render(request, "core/vendor_register.html", {
        "success": success,
        "error": error,
    })