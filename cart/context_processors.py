from .models import Cart
# pyrefly: ignore [missing-import]
from django.db import DatabaseError

def cart_count(request):
    if request.user.is_authenticated:
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            return {'cart_count': cart.total_items}
        except (DatabaseError, Exception):
            return {'cart_count': 0}
    return {'cart_count': 0}
