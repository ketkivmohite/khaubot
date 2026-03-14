import httpx
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST

FASTAPI_URL = settings.KHAUBOT_API_URL.rstrip("/")

def home(request):
    return render(request, "core/home.html")


@require_POST
def discover_chat(request):
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    query = (body.get("query") or "").strip()
    if not query:
        return JsonResponse({"error": "Query is required."}, status=400)

    try:
        response = httpx.post(
            f"{FASTAPI_URL}/api/discover",
            json={"query": query},
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        return JsonResponse(
            {
                "query": data.get("query", query),
                "detected_language": data.get("detected_language", "unknown"),
                "extracted_intent": data.get("extracted_intent", "food_search"),
                "results": data.get("results", []),
            },
            status=200,
        )
    except httpx.RequestError:
        return JsonResponse(
            {"error": f"Could not reach backend at {FASTAPI_URL}."},
            status=503,
        )
    except httpx.HTTPStatusError as e:
        return JsonResponse(
            {"error": f"Backend error {e.response.status_code}: {e.response.text[:200]}"},
            status=502,
        )
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


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
                timeout=10.0,
                follow_redirects=True,
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


def khaubot_admin(request):
    error = None
    vendors = []

    try:
        response = httpx.get(
            f"{FASTAPI_URL}/api/vendor/all",
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        vendors = response.json()
    except Exception as e:
        error = f"Could not load vendors: {str(e)}"

    return render(request, "core/khaubot_admin.html", {
        "vendors": vendors,
        "error": error,
        "success": request.GET.get("success"),
    })


def admin_approve(request, vendor_id):
    try:
        httpx.patch(
            f"{FASTAPI_URL}/api/vendor/{vendor_id}/approve",
            timeout=10.0,
            follow_redirects=True,
        )
    except Exception:
        pass
    return redirect("/khaubot-admin/?success=approved")


def admin_reject(request, vendor_id):
    try:
        httpx.patch(
            f"{FASTAPI_URL}/api/vendor/{vendor_id}/reject",
            timeout=10.0,
            follow_redirects=True,
        )
    except Exception:
        pass
    return redirect("/khaubot-admin/?success=rejected")