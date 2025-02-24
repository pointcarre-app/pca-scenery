"""
URL configuration for django_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path

from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

try:
    from rehearsal.django_project.some_app import views
except ModuleNotFoundError:
    # NOTE: mypy should run from the root directory
    # and therefore it make sense that this module is not found
    from some_app import views  # type: ignore[import-not-found, no-redef]

# app_name = "some_app"
urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
    path('http', views.hello_http, name='http'),
    path('', views.hello_rendered, name='frontend'),
]


