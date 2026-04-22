"""
URL configuration for settings project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.schemas import get_schema_view

schema_view = get_schema_view(
    title="Mabalacat City Government API",
    version="1.0.0",
    description="API schema for Mabalacat City Government systems.",
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('docs/', schema_view, name='api-schema'),
    path('api/payroll/', include('payroll_system.urls')),
    path('api/hr/', include('hr_records_management.urls')),
    path('api/recruitment/', include('recruitment_selection_placement.urls')),
    path('api/auth/', include('auth_app.urls')),
    path('api/shared/', include('shared.urls'))
]
