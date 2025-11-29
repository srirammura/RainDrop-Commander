from django.contrib import admin
from django.urls import path
from commander import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", views.health_check, name="health"),
    path("effort-stats", views.effort_stats, name="effort_stats"),
    path("", views.home, name="home"),
]

