"""
URL configuration for main project.

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
from django.urls import path
from core.views import basic_contact_view, contact_view, success_view
from core.views import create_cv, cv_list, share_cv_email, cv_detail
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('basic-contact/', basic_contact_view, name='basic_contact'),
    path('contact/', contact_view, name='contact'),
    path('success/', success_view, name='success_page'),
    path('cv/create/', create_cv, name='create_cv'),
    path('cv/list/', cv_list, name='cv_list'),
    path('cv/<int:cv_id>/', cv_detail, name='cv_detail'),
    path('share/email/<int:cv_id>/', share_cv_email, name='share_cv_email'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
