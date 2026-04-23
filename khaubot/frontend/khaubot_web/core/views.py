import httpx
import json
import requests as req
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from core.models import UserProfile

FASTAPI_URL = settings.KHAUBOT_API_URL.rstrip("/")
ADMIN_USERNAME = "ketki"


# ── OSM direct search — works even when FastAPI is down ──────────

def search_osm_django(query: str) -> list:
    """Search real Mumbai food places directly from Django using OpenStreetMap."""

    MUMBAI_AREAS = [
        "bandra", "andheri", "juhu", "colaba", "dadar", "kurla",
        "borivali", "malad", "goregaon", "powai", "thane", "worli",
        "lower parel", "matunga", "sion", "chembur", "mulund",
        "versova", "mahim", "khar", "santacruz", "vile parle",
        "kandivali", "mira road", "dharavi", "ghatkopar", "mulund",
        "vikhroli", "bhandup", "nahur", "wadala", "parel", "sewri",
    ]

    query_lower = query.lower()
    area = ""
    for a in MUMBAI_AREAS:
        if a in query_lower:
            area = a
            break

    # Geocode area to lat/lng
    lat, lng = 19.0760, 72.8777  # Mumbai center default
    if area:
        try:
            geo = req.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{area}, Mumbai, India", "format": "json", "limit": 1},
                headers={"User-Agent": "KhauBot/1.0 (khaubot-171u.vercel.app)"},
                timeout=5
            )
            geo_results = geo.json()
            if geo_results:
                lat = float(geo_results[0]["lat"])
                lng = float(geo_results[0]["lon"])
        except Exception:
            pass

    # Search OpenStreetMap
    try:
        osm_query = f"""
        [out:json][timeout:10];
        node["amenity"~"restaurant|cafe|fast_food|food_court|bar|street_vendor"]["name"]
        (around:5000,{lat},{lng});
        out body;
        """
        resp = req.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": osm_query},
            headers={"User-Agent": "KhauBot/1.0 (khaubot-171u.vercel.app)"},
            timeout=12
        )
        elements = resp.json().get("elements", [])
        results = []
        for el in elements[:10]:
            tags = el.get("tags", {})
            name = tags.get("name", "")
            if not name:
                continue
            results.append({
                "id": el.get("id"),
                "name": name,
                "area": area or "Mumbai",
                "address": tags.get("addr:street", "Mumbai"),
                "cuisine": tags.get("cuisine", ""),
                "category": tags.get("amenity", ""),
                "operating_hours": tags.get("opening_hours", ""),
                "whatsapp": "",
                "price_min": None,
                "price_max": None,
                "signature_dishes": "",
                "source": "osm",
            })
        return results
    except Exception:
        return []


# ── Views ────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def home(request):
    return render(request, "core/home.html")


@login_required(login_url='/login/')
@require_POST
def discover_chat(request):
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    query = (body.get("query") or "").strip()
    if not query:
        return JsonResponse({"error": "Query is required."}, status=400)

    # Try FastAPI first
    try:
        response = httpx.post(
            f"{FASTAPI_URL}/api/discover",
            json={"query": query},
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if results:
            return JsonResponse({
                "query": data.get("query", query),
                "detected_language": data.get("detected_language", "unknown"),
                "extracted_intent": data.get("extracted_intent", {}),
                "results": results,
            }, status=200)
    except Exception:
        pass

    # FastAPI failed or returned empty — search OSM directly
    results = search_osm_django(query)
    return JsonResponse({
        "query": query,
        "detected_language": "en",
        "extracted_intent": {},
        "results": results,
    }, status=200)


def vendor_register(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        if request.user.profile.user_type != 'vendor':
            return redirect('/')
    except:
        return redirect('/')

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
    if not request.user.is_authenticated or request.user.username != ADMIN_USERNAME:
        return redirect('/login/')

    error = None
    vendors = []
    users = []

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

    try:
        users = User.objects.all().order_by("-date_joined").values(
            "id", "username", "email", "date_joined", "is_staff", "is_active"
        )
    except Exception as e:
        error = f"Could not load users: {str(e)}"

    return render(request, "core/khaubot_admin.html", {
        "vendors": vendors,
        "error": error,
        "success": request.GET.get("success"),
        "users": users,
    })


def admin_approve(request, vendor_id):
    if not request.user.is_authenticated or request.user.username != ADMIN_USERNAME:
        return redirect('/login/')
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
    if not request.user.is_authenticated or request.user.username != ADMIN_USERNAME:
        return redirect('/login/')
    try:
        httpx.patch(
            f"{FASTAPI_URL}/api/vendor/{vendor_id}/reject",
            timeout=10.0,
            follow_redirects=True,
        )
    except Exception:
        pass
    return redirect("/khaubot-admin/?success=rejected")


def user_login(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            error = "Invalid username or password."
    return render(request, "core/login.html", {"error": error})


def user_signup(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        user_type = request.POST.get("user_type", "user")
        email = request.POST.get("email", "").strip()

        if password != password2:
            error = "Passwords do not match."
        elif not email:
            error = "Email is required."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        elif User.objects.filter(email=email).exists():
            error = "An account with this email already exists."
        else:
            user = User.objects.create_user(username=username, password=password, email=email)
            UserProfile.objects.create(user=user, user_type=user_type)
            user = authenticate(request, username=username, password=password)
            login(request, user)

            if user_type == 'vendor':
                try:
                    payload = {
                        "name": request.POST.get("name", ""),
                        "category": request.POST.get("category", "street_stall"),
                        "area": request.POST.get("area", ""),
                        "address": request.POST.get("address", ""),
                        "cuisine": request.POST.get("cuisine", ""),
                        "signature_dishes": request.POST.get("signature_dishes", ""),
                        "price_min": int(request.POST.get("price_min") or 0),
                        "price_max": int(request.POST.get("price_max") or 0),
                        "operating_hours": request.POST.get("operating_hours", ""),
                        "open_days": request.POST.get("open_days", ""),
                        "contact": request.POST.get("contact", ""),
                        "whatsapp_link": request.POST.get("whatsapp_link", ""),
                        "photo_url": "",
                    }
                    httpx.post(
                        f"{FASTAPI_URL}/api/vendor/register",
                        json=payload,
                        timeout=10.0,
                        follow_redirects=True,
                    )
                except Exception:
                    pass

            return redirect("/")

    return render(request, "core/signup.html", {"error": error})


def user_logout(request):
    logout(request)
    return redirect("/login/")