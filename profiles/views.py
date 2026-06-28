# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.contrib import messages
from core.supabase_client import supabase
import time
# pyrefly: ignore [missing-import]
from django.contrib.auth.forms import PasswordChangeForm
# pyrefly: ignore [missing-import]
from django.contrib.auth import update_session_auth_hash


# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import user_passes_test
# pyrefly: ignore [missing-import]
from django.db.models import Sum, Q
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.shortcuts import get_object_or_404
from products.models import Product, Category
from cart.models import Order
from accounts.models import UserProfile


@login_required(login_url='login')
def profile_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Simple validations
        if not email:
            messages.error(request, "Email address is required.")
        else:
            try:
                user.email = email
                user.save()
                
                if profile:
                    profile.full_name = full_name
                    profile.phone_number = phone_number
                    profile.address = address
                    
                    # Handle profile picture upload to Supabase Storage
                    if 'avatar' in request.FILES:
                        avatar_file = request.FILES['avatar']
                        ext = avatar_file.name.split('.')[-1]
                        # Create a unique filename based on user ID and timestamp to avoid caching/conflict
                        file_name = f"user_{user.id}_{int(time.time())}.{ext}"
                        
                        try:
                            from core.supabase_client import upload_file
                            # Read file content as bytes
                            file_data = avatar_file.read()
                            content_type = avatar_file.content_type
                            
                            # Upload to 'user' bucket and get public URL
                            public_url = upload_file(
                                bucket_name="user",
                                file_name=file_name,
                                file_data=file_data,
                                content_type=content_type
                            )
                            profile.avatar_url = public_url
                            
                        except Exception as storage_err:
                            messages.warning(request, f"Profile updated, but avatar upload failed: {str(storage_err)}")
                    
                    profile.save()
                
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('profile')
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                
    return render(request, 'profile.html', {
        'profile': profile
    })

@login_required(login_url='login')
def settings_view(request):    
    profile = getattr(request.user, 'profile', None)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'security':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been updated successfully!')
                return redirect('settings')
            else:
                # Keep active tab as security on form errors
                return render(request, 'settings.html', {
                    'profile': profile,
                    'form': form,
                    'active_tab': 'security'
                })
                
        elif action == 'preferences':
            # Save mock preference switches
            messages.success(request, 'System and notification preferences saved successfully!')
            return redirect('settings')
            
    form = PasswordChangeForm(request.user)
    return render(request, 'settings.html', {
        'profile': profile,
        'form': form,
        'active_tab': 'preferences'
    })

# Helper to check if the user is an admin
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user.profile, 'role', '') == 'admin')

@user_passes_test(is_admin, login_url='login')
def admin_dashboard(request):    
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_customers = UserProfile.objects.filter(role='user').count()
    
    total_orders = Order.objects.count()
    total_sales = Order.objects.exclude(status='cancelled').aggregate(total=Sum('grand_total'))['total'] or 0
    
    recent_customers = UserProfile.objects.filter(role='user').order_by('-id')[:5]
    recent_products = Product.objects.all().order_by('-id')[:5]
    recent_orders = Order.objects.all().order_by('-id')[:10].prefetch_related('items')
    
    return render(request, 'admin_dashboard.html', {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'recent_customers': recent_customers,
        'recent_products': recent_products,
        'recent_orders': recent_orders,
    })

@user_passes_test(is_admin, login_url='login')
def manage_customers(request):    
    # Handle POST action (role updates / deletes / profile edits)
    if request.method == 'POST':
        action = request.POST.get('action')
        customer_id = request.POST.get('customer_id')
        profile = get_object_or_404(UserProfile, id=customer_id)
        user = profile.user
        
        if action == 'toggle_role':
            new_role = 'admin' if profile.role == 'user' else 'user'
            profile.role = new_role
            profile.save()
            
            # Synchronise Django is_staff/is_superuser flags
            user.is_staff = (new_role == 'admin')
            user.is_superuser = (new_role == 'admin')
            user.save()
            
            messages.success(request, f"Updated role for {user.username} to {new_role.upper()}.")
            
        elif action == 'toggle_status':
            if user == request.user:
                messages.error(request, "You cannot suspend your own account.")
            else:
                profile.is_suspended = not profile.is_suspended
                profile.save()
                
                # Sync with Django's built-in active status
                user.is_active = not profile.is_suspended
                user.save()
                
                status_str = "suspended" if profile.is_suspended else "activated"
                messages.success(request, f"Successfully {status_str} account for '{user.username}'.")
            
        elif action == 'edit':
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address = request.POST.get('address', '').strip()
            role = request.POST.get('role', 'user')
            is_suspended = request.POST.get('is_suspended') == 'true'
            
            # Block self-suspension
            if user == request.user and is_suspended:
                messages.error(request, "You cannot suspend your own account.")
                is_suspended = False
            
            # Simple updates
            profile.full_name = full_name
            profile.phone_number = phone_number
            profile.address = address
            profile.role = role
            profile.is_suspended = is_suspended
            profile.save()
            
            user.email = email
            user.is_staff = (role == 'admin')
            user.is_superuser = (role == 'admin')
            user.is_active = not is_suspended
            user.save()
            
            messages.success(request, f"Updated details for customer '{user.username}'.")
            
        elif action == 'delete':
            # Block self-deletion
            if user == request.user:
                messages.error(request, "You cannot delete your own account.")
            else:
                username = user.username
                user.delete()
                messages.success(request, f"Customer account '{username}' has been deleted successfully.")
                
        return redirect('manage_customers')
        
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    
    customers = UserProfile.objects.all().select_related('user').order_by('-id')
    
    if search_query:
        customers = customers.filter(
            Q(full_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
        
    if role_filter in ['admin', 'user']:
        customers = customers.filter(role=role_filter)
        
    # Gather orders statistics for each customer
    customer_list = []
    for profile in customers:
        orders_query = Order.objects.filter(user=profile.user)
        order_count = orders_query.count()
        total_spend = orders_query.exclude(status='cancelled').aggregate(total=Sum('grand_total'))['total'] or 0
        customer_list.append({
            'profile': profile,
            'order_count': order_count,
            'total_spend': total_spend,
        })
        
    context = {
        'customers': customer_list,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    
    return render(request, 'manage_customers.html', context)
