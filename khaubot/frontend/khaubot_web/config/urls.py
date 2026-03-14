from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('api/discover/', views.discover_chat, name='discover_chat'),
    path('vendor/', views.vendor_register, name='vendor'),
    path('register/', views.vendor_register, name='vendor_register'),
    path('khaubot-admin/', views.khaubot_admin, name='khaubot_admin'),
    path('khaubot-admin/approve/<int:vendor_id>/', views.admin_approve, name='admin_approve'),
    path('khaubot-admin/reject/<int:vendor_id>/', views.admin_reject, name='admin_reject'),
]