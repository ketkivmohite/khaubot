import httpx
import json
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

        if password != password2:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        else:
            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(user=user, user_type=user_type)
            user = authenticate(request, username=username, password=password)
            login(request, user)
            return redirect("/")
    return render(request, "core/signup.html", {"error": error})


def user_logout(request):
    logout(request)
    return redirect("/login/")