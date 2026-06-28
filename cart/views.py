# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.views.decorators.http import require_POST
# pyrefly: ignore [missing-import]
from django.contrib import messages
from products.models import Product
from .models import Cart, CartItem, Order, OrderItem
import time
from core.supabase_client import upload_file

# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import user_passes_test
# pyrefly: ignore [missing-import]
from django.db.models import Sum, Q

@login_required(login_url='login')
def cart_list(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all().select_related('product')
    return render(request, 'cart.html', {
        'cart': cart,
        'items': items,
    })

@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.stock <= 0:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect('list_products')
        
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    # Read custom quantity parameter if provided
    quantity_to_add = 1
    if request.method == 'POST':
        try:
            quantity_to_add = int(request.POST.get('quantity', 1))
            if quantity_to_add < 1:
                quantity_to_add = 1
        except ValueError:
            quantity_to_add = 1
            
    if not item_created:
        # Check stock limits
        target_quantity = cart_item.quantity + (quantity_to_add if 'quantity' in request.POST else 1)
        if target_quantity <= product.stock:
            cart_item.quantity = target_quantity
            cart_item.save()
            messages.success(request, f"Updated quantity of {product.name} in your cart.")
        else:
            if cart_item.quantity < product.stock:
                cart_item.quantity = product.stock
                cart_item.save()
                messages.warning(request, f"Only added up to stock limit ({product.stock} items).")
            else:
                messages.warning(request, f"Cannot add more of {product.name}. Stock limit reached.")
    else:
        # New item
        if quantity_to_add <= product.stock:
            cart_item.quantity = quantity_to_add
        else:
            cart_item.quantity = product.stock
            messages.warning(request, f"Only added up to stock limit ({product.stock} items).")
        cart_item.save()
        messages.success(request, f"Added {product.name} to your cart.")
        
    # Redirect back to where the user came from or the cart page
    next_url = request.GET.get('next', 'cart_list')
    return redirect(next_url)

@login_required(login_url='login')
@require_POST
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    action = request.POST.get('action')
    
    if action == 'increase':
        if cart_item.quantity < cart_item.product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"Increased quantity of {cart_item.product.name}.")
        else:
            messages.warning(request, f"Stock limit reached for {cart_item.product.name}.")
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            messages.success(request, f"Decreased quantity of {cart_item.product.name}.")
        else:
            cart_item.delete()
            messages.success(request, f"Removed {cart_item.product.name} from your cart.")
    
    return redirect('cart_list')

@login_required(login_url='login')
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f"Removed {product_name} from your cart.")
    return redirect('cart_list')


@login_required(login_url='login')
def checkout_view(request):
    user = request.user
    cart, created = Cart.objects.get_or_create(user=user)
    items = cart.items.all().select_related('product')
    
    # If cart is empty, redirect back to cart
    if not items.exists():
        messages.warning(request, "Your cart is empty. Add products before checking out.")
        return redirect('cart_list')
        
    profile = getattr(user, 'profile', None)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Simple validations
        if not full_name or not phone_number or not address:
            messages.error(request, "Please fill in all recipient details.")
            return render(request, 'checkout.html', {
                'cart': cart,
                'items': items,
                'full_name': full_name,
                'phone_number': phone_number,
                'address': address,
            })
            
        if 'payment_proof' not in request.FILES:
            messages.error(request, "Please upload your proof of transfer/payment receipt.")
            return render(request, 'checkout.html', {
                'cart': cart,
                'items': items,
                'full_name': full_name,
                'phone_number': phone_number,
                'address': address,
            })
            
        payment_proof_file = request.FILES['payment_proof']
        ext = payment_proof_file.name.split('.')[-1]
        file_name = f"proof_{user.id}_{int(time.time())}.{ext}"
        
        try:
            # Upload receipt to Supabase Storage in 'payments' bucket
            file_data = payment_proof_file.read()
            content_type = payment_proof_file.content_type
            
            public_url = upload_file(
                bucket_name="payments",
                file_name=file_name,
                file_data=file_data,
                content_type=content_type
            )
            
            # Create Order
            order = Order.objects.create(
                user=user,
                full_name=full_name,
                phone_number=phone_number,
                address=address,
                total_price=cart.total_price,
                shipping_cost=cart.shipping_cost,
                grand_total=cart.grand_total,
                payment_proof_url=public_url,
                status='pending'
            )
            
            # Create OrderItems and decrease stock
            for cart_item in items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity
                )
                # Decrease product stock
                product = cart_item.product
                if product.stock >= cart_item.quantity:
                    product.stock -= cart_item.quantity
                else:
                    product.stock = 0
                product.save()
                
            # Clear the cart items
            items.delete()
            
            messages.success(request, f"Thank you! Your order #{order.id} has been placed successfully and is awaiting payment verification.")
            return redirect('order_history')
            
        except Exception as upload_err:
            messages.error(request, f"Checkout failed: Could not upload proof of payment. {str(upload_err)}")
            
    # GET: Pre-populate fields from profile
    initial_name = profile.full_name if profile else ""
    initial_phone = profile.phone_number if profile else ""
    initial_address = profile.address if profile else ""
    
    return render(request, 'checkout.html', {
        'cart': cart,
        'items': items,
        'full_name': initial_name,
        'phone_number': initial_phone,
        'address': initial_address,
    })

@login_required(login_url='login')
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'order_history.html', {
        'orders': orders,
    })

# Helper to check if the user is an admin
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user.profile, 'role', '') == 'admin')

@user_passes_test(is_admin, login_url='login')
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        status = request.POST.get('status')
        if status in ['pending', 'processing', 'shipped', 'completed', 'cancelled']:
            order.status = status
            order.save()
            messages.success(request, f"Order #{order.id} status updated to {status.capitalize()}.")
        else:
            messages.error(request, "Invalid order status value.")
    # Redirect back to where the request came from (Referer) or fallback to dashboard
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('admin_dashboard')

@user_passes_test(is_admin, login_url='login')
def manage_orders(request):
    # Prefetch related data to optimize query count
    orders = Order.objects.all().select_related('user').prefetch_related('items__product').order_by('-created_at')
    
    # Summary Metrics
    total_orders_count = Order.objects.count()
    total_revenue = Order.objects.exclude(status='cancelled').aggregate(total=Sum('grand_total'))['total'] or 0
    pending_orders_count = Order.objects.filter(status='pending').count()
    completed_orders_count = Order.objects.filter(status='completed').count()
    
    # Filtering and searching parameters
    status_filter = request.GET.get('status', '').strip().lower()
    search_query = request.GET.get('search', '').strip()
    
    if status_filter in ['pending', 'processing', 'shipped', 'completed', 'cancelled']:
        orders = orders.filter(status=status_filter)
        
    if search_query:
        clean_search = search_query
        if clean_search.startswith('#'):
            clean_search = clean_search[1:]
        try:
            # If search contains numerical order ID
            order_id = int(clean_search)
            orders = orders.filter(
                Q(id=order_id) | 
                Q(user__username__icontains=search_query) |
                Q(full_name__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(items__product_name__icontains=search_query)
            ).distinct()
        except ValueError:
            orders = orders.filter(
                Q(user__username__icontains=search_query) |
                Q(full_name__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(items__product_name__icontains=search_query)
            ).distinct()
            
    context = {
        'orders': orders,
        'total_orders_count': total_orders_count,
        'total_revenue': total_revenue,
        'pending_orders_count': pending_orders_count,
        'completed_orders_count': completed_orders_count,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'manage_orders.html', context)
