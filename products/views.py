# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import user_passes_test
# pyrefly: ignore [missing-import]
from django.contrib import messages
from .models import Category, Product
import time
# pyrefly: ignore [missing-import]
from django.utils.text import slugify

# pyrefly: ignore [missing-import]
from django.urls import reverse
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.db.models import Q

# Helper to check if the user is an admin
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user.profile, 'role', '') == 'admin')

@user_passes_test(is_admin, login_url='login')
def manage_products(request):
    # Auto-create categories if they don't exist
    if not Category.objects.exists():
        Category.objects.create(name="Mouse", slug="mouse")
        Category.objects.create(name="Keyboard", slug="keyboard")
        Category.objects.create(name="Headset", slug="headset")
        Category.objects.create(name="Monitor", slug="monitor")

    categories = Category.objects.all()
    products = Product.objects.all().order_by('-id')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            description = request.POST.get('description', '').strip()
            price = request.POST.get('price', '0')
            stock = request.POST.get('stock', '0')
            image_url = request.POST.get('image_url', '').strip()
            
            category = get_object_or_404(Category, id=category_id)
            
            # Handle image file upload to Supabase 'product' bucket
            if 'image_file' in request.FILES:
                image_file = request.FILES['image_file']
                ext = image_file.name.split('.')[-1]
                file_name = f"product_{int(time.time())}.{ext}"
                try:
                    from core.supabase_client import upload_file
                    file_data = image_file.read()
                    content_type = image_file.content_type
                    image_url = upload_file(
                        bucket_name="product",
                        file_name=file_name,
                        file_data=file_data,
                        content_type=content_type
                    )
                except Exception as e:
                    messages.error(request, f"Image upload failed: {str(e)}")
                    
            try:
                Product.objects.create(
                    category=category,
                    name=name,
                    description=description,
                    price=price,
                    stock=stock,
                    image_url=image_url
                )
                messages.success(request, f"Product '{name}' created successfully!")
            except Exception as e:
                messages.error(request, f"Error creating product: {str(e)}")
                
        elif action == 'update':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            
            product.name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            product.category = get_object_or_404(Category, id=category_id)
            product.description = request.POST.get('description', '').strip()
            product.price = request.POST.get('price', '0')
            product.stock = request.POST.get('stock', '0')
            
            # If new file is uploaded
            if 'image_file' in request.FILES:
                image_file = request.FILES['image_file']
                ext = image_file.name.split('.')[-1]
                file_name = f"product_{int(time.time())}.{ext}"
                try:
                    from core.supabase_client import upload_file
                    file_data = image_file.read()
                    content_type = image_file.content_type
                    product.image_url = upload_file(
                        bucket_name="product",
                        file_name=file_name,
                        file_data=file_data,
                        content_type=content_type
                    )
                except Exception as e:
                    messages.error(request, f"Image upload failed: {str(e)}")
            else:
                # If they pasted a new text URL
                image_url_input = request.POST.get('image_url', '').strip()
                if image_url_input:
                    product.image_url = image_url_input
            
            try:
                product.save()
                messages.success(request, f"Product '{product.name}' updated successfully!")
            except Exception as e:
                messages.error(request, f"Error updating product: {str(e)}")
                
        elif action == 'delete':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            name = product.name
            try:
                product.delete()
                messages.success(request, f"Product '{name}' deleted successfully!")
            except Exception as e:
                messages.error(request, f"Error deleting product: {str(e)}")
                
        return redirect('manage_products')
        
    return render(request, 'manage_products.html', {
        'products': products,
        'categories': categories
    })

@user_passes_test(is_admin, login_url='login')
def manage_categories(request):
    categories = Category.objects.all().order_by('id')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name', '').strip()
            slug_input = request.POST.get('slug', '').strip()
            
            if not name:
                messages.error(request, "Category name is required.")
            else:
                slug = slug_input if slug_input else slugify(name)
                
                # Check uniqueness
                if Category.objects.filter(name__iexact=name).exists():
                    messages.error(request, f"Category with name '{name}' already exists.")
                elif Category.objects.filter(slug=slug).exists():
                    messages.error(request, f"Category with slug '{slug}' already exists.")
                else:
                    try:
                        Category.objects.create(name=name, slug=slug)
                        messages.success(request, f"Category '{name}' created successfully!")
                    except Exception as e:
                        messages.error(request, f"Error creating category: {str(e)}")
                        
        elif action == 'update':
            category_id = request.POST.get('category_id')
            category = get_object_or_404(Category, id=category_id)
            
            name = request.POST.get('name', '').strip()
            slug_input = request.POST.get('slug', '').strip()
            
            if not name:
                messages.error(request, "Category name is required.")
            else:
                slug = slug_input if slug_input else slugify(name)
                
                # Check uniqueness excluding self
                if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
                    messages.error(request, f"Category with name '{name}' already exists.")
                elif Category.objects.filter(slug=slug).exclude(id=category_id).exists():
                    messages.error(request, f"Category with slug '{slug}' already exists.")
                else:
                    try:
                        category.name = name
                        category.slug = slug
                        category.save()
                        messages.success(request, f"Category '{name}' updated successfully!")
                    except Exception as e:
                        messages.error(request, f"Error updating category: {str(e)}")
                        
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            category = get_object_or_404(Category, id=category_id)
            name = category.name
            try:
                category.delete()
                messages.success(request, f"Category '{name}' deleted successfully!")
            except Exception as e:
                messages.error(request, f"Error deleting category: {str(e)}")
                
        return redirect('manage_categories')
        
    return render(request, 'manage_categories.html', {
        'categories': categories
    })

def list_products(request):
    products = Product.objects.all().order_by('-id')
    categories = Category.objects.all().order_by('name')
    return render(request, 'list_product.html', {
        'products': products,
        'categories': categories
    })



def product_detail(request, product_id, slug=None):
    product = get_object_or_404(Product, id=product_id)
    correct_slug = slugify(product.name)
    
    # 301 Redirect for SEO canonicalization
    if slug != correct_slug:
        return redirect('product_detail', product_id=product.id, slug=correct_slug, permanent=True)
    
    # Related products in the same category (excluding current, limit to 4)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    
    canonical_url = request.build_absolute_uri(
        reverse('product_detail', args=[product.id, correct_slug])
    )
    
    context = {
        'product': product,
        'related_products': related_products,
        'canonical_url': canonical_url,
        'title': f"{product.name} | GearZone",
        'description': product.description[:155] if product.description else f"Buy {product.name} at GearZone. Premium gaming gear.",
        'keywords': f"{product.name}, {product.category.name}, gaming gear, gearzone",
        'og_image': product.image_url if product.image_url else None,
    }
    
    return render(request, 'detail_product.html', context)



def product_search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse([], safe=False)

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).select_related('category')[:6]

    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'image_url': p.image_url,
            'category': p.category.name,
            'url': reverse('product_detail', args=[p.id, slugify(p.name)]),
        })

    return JsonResponse(results, safe=False)
