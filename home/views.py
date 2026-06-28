# pyrefly: ignore [missing-import]
from django.shortcuts import render
from products.models import Category, Product

def index(request):
    categories = Category.objects.all().order_by('name')[:4]
    products = Product.objects.all().order_by('-id')[:4]
    return render(request, 'home.html', {
        'categories': categories,
        'products': products
    })
