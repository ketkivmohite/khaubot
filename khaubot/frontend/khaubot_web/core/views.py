import httpx
from django.shortcuts import render
from django.conf import settings

FASTAPI_URL = settings.KHAUBOT_API_URL

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
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
        except httpx.RequestError:
            error = f"Could not reach backend at {FASTAPI_URL}."
        except httpx.HTTPStatusError as e:
            error = f"Backend error {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            error = f"Unexpected error: {str(e)}"

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
            response.raise_for_status()
            if response.status_code == 201:
                success = True
            else:
                error = "Registration failed. Please try again."
        except httpx.RequestError:
            error = f"Could not reach backend at {FASTAPI_URL}."
        except httpx.HTTPStatusError as e:
            error = f"Backend error {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            error = f"Unexpected error: {str(e)}"

    return render(request, "core/vendor_register.html", {
        "success": success,
        "error": error,
    })