from .models import CartItem

def cart_count(request):
    """
    Context processor to make the total cart item count available in all templates.
    """
    if request.user.is_authenticated:
        # Sum of quantities for all items in the user's cart
        items = CartItem.objects.filter(cart__user=request.user)
        return {'cart_count': sum(item.quantity for item in items)}
    return {'cart_count': 0}
