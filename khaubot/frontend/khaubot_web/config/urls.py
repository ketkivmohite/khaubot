from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('api/discover/', views.discover_chat, name='discover_chat'),
    path('vendor/', views.vendor_register, name='vendor'),
    path('register/', views.vendor_register, name='vendor_register'),
]