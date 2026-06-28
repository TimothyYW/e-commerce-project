"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import path, include
# pyrefly: ignore [missing-import]
from profiles import views as profiles_views
from cart import views as cart_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('auth/', include('accounts.urls')),
    path('profile/', include('profiles.urls')),
    path('product/', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('settings/', profiles_views.settings_view, name='settings'),
    path('dashboard/', profiles_views.admin_dashboard, name='admin_dashboard'),
    path('customers/', profiles_views.manage_customers, name='manage_customers'),
    path('orders/', cart_views.manage_orders, name='manage_orders'),
    path('order/<int:order_id>/status/', cart_views.update_order_status, name='update_order_status'),
]
