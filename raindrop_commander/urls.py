from django.contrib import admin
from django.urls import path
from commander import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", views.health_check, name="health"),
    path("", views.home, name="home"),
]

