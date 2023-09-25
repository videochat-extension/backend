"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from api.views import geo, whoami, get_users, submit_bug, patron_geo, webhook_patreon, webhook_canny
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic.base import TemplateView, RedirectView

urlpatterns = [

    # These URLs shadow django-allauth URLs to shut them down:
    path('accounts/password/change/', RedirectView.as_view(url='/')),
    path('accounts/password/set/', RedirectView.as_view(url='/')),
    path('accounts/password/reset/', RedirectView.as_view(url='/')),
    path('accounts/password/reset/done/', RedirectView.as_view(url='/')),
    re_path('accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$', RedirectView.as_view(url='/')),
    path('accounts/password/reset/key/done/', RedirectView.as_view(url='/')),
    path('accounts/email/', RedirectView.as_view(url='/')),
    path('accounts/confirm-email/', RedirectView.as_view(url='/')),
    path('accounts/singup/', RedirectView.as_view(url='/')),
    path('accounts/login/', RedirectView.as_view(url='/')),
    re_path('accounts/confirm-email/(?P<key>[-:\\w]+)/$', RedirectView.as_view(url='/')),

    # path('admin/', admin.site.urls),
    path('geo', geo),
    path('users', get_users),
    path('report-bug', submit_bug),
    path('patron-geo', patron_geo),
    path('whoami', whoami),
    path('webhook_patreon', webhook_patreon),
    path('webhook_canny', webhook_canny),


    path("", TemplateView.as_view(template_name="index.html")),
    path("accounts/", include("allauth.urls")),
    path("accounts/profile/", TemplateView.as_view(template_name="profile.html")),
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
