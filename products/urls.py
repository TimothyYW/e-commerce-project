# pyrefly: ignore [missing-import]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_products, name='list_products'),
    path('manage/', views.manage_products, name='manage_products'),
    path("category/", views.manage_categories, name='manage_categories'),
    path('search-suggestions/', views.product_search_suggestions, name='product_search_suggestions'),
    path('<int:product_id>/', views.product_detail, name='product_detail_simple'),
    path('<int:product_id>/<slug:slug>/', views.product_detail, name='product_detail'),
]
