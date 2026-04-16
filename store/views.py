import json
import hmac
import hashlib

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta
from django.db import transaction

from .forms import AddressForm, LoginForm, UserRegistrationForm
from .models import Clothing, Category, RentalOrder, RazorpayPayment, UserAddress, Cart, CartItem, Wallet, WalletTransaction

MIN_RENTAL_DAYS = 1
MAX_RENTAL_DAYS = 30

# ─────────────────────────────────────────────────────────────────────────────
# Public Views
# ─────────────────────────────────────────────────────────────────────────────

def home(request):
    featured = Clothing.objects.filter(is_available=True, is_featured=True)
    return render(request, 'home.html', {'featured': featured})

def browse(request):
    clothes = Clothing.objects.filter(is_available=True)
    gender = request.GET.get('gender')
    size = request.GET.get('size')
    if gender:
        clothes = clothes.filter(gender=gender)
    if size:
        clothes = clothes.filter(size=size)
    return render(request, 'browse.html', {'items': clothes})

def collections(request):
    return render(request, 'collections.html')

def how_it_works(request):
    return render(request, 'how_it_works.html')

def product_detail(request, id):
    product = get_object_or_404(Clothing, id=id)
    return render(request, 'product_detail.html', {'product': product})

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    clothes = Clothing.objects.filter(category=category, is_available=True)
    gender = request.GET.get('gender')
    size = request.GET.get('size')
    if gender:
        clothes = clothes.filter(gender=gender)
    if size:
        clothes = clothes.filter(size=size)
    return render(request, 'browse.html', {
        'items': clothes,
        'selected_category': category,
    })

# ─────────────────────────────────────────────────────────────────────────────
# Auth Views
# ─────────────────────────────────────────────────────────────────────────────

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Account created for {user.username}!')
            login(request, user)
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            from django.contrib.auth.models import User
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name}!')
                    return redirect('home')
                else:
                    form.add_error(None, 'Invalid email or password.')
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                form.add_error(None, 'Invalid email or password.')
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# ─────────────────────────────────────────────────────────────────────────────
# Payment Page
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_page(request, product_id):
    product = get_object_or_404(Clothing, id=product_id, is_available=True)
    last_address = UserAddress.objects.filter(user=request.user).order_by('-created_at').first()

    context = {
        'product': product,
        'min_days': MIN_RENTAL_DAYS,
        'max_days': MAX_RENTAL_DAYS,
        'last_address': last_address,
        'min_rental_days': MIN_RENTAL_DAYS,
        'max_rental_days': MAX_RENTAL_DAYS,
        'booked_orders': RentalOrder.objects.filter(
            product=product, status='confirmed'
        ).values('start_date', 'end_date'),
        # Pass key_id to template (safe – never pass secret key here)
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'payment.html', context)

# ─────────────────────────────────────────────────────────────────────────────
# Razorpay: Create Order  (called via AJAX from the frontend)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def create_razorpay_order(request, product_id):
    """
    POST /product/<id>/create-razorpay-order/
    Reads rental_days from the request body and creates a Razorpay order.
    Returns { order_id, amount, currency, key_id } as JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    product = get_object_or_404(Clothing, id=product_id, is_available=True)

    try:
        body      = json.loads(request.body)
        rental_days = int(body.get('rental_days', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if rental_days < MIN_RENTAL_DAYS or rental_days > MAX_RENTAL_DAYS:
        return JsonResponse({'error': f'Rental days must be between {MIN_RENTAL_DAYS} and {MAX_RENTAL_DAYS}'}, status=400)

    # Calculate amount in paise (Razorpay uses smallest currency unit)
    rent_total   = product.price_per_day * rental_days
    total_amount = rent_total + product.security_deposit
    amount_paise = int(total_amount * 100)  # convert ₹ → paise

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        razorpay_order = client.order.create({
            'amount':   amount_paise,
            'currency': 'INR',
            'payment_capture': 1,   # auto-capture
            'notes': {
                'product_id':   str(product_id),
                'rental_days':  str(rental_days),
                'user_id':      str(request.user.id),
                'rent_amount':  str(rent_total),
                'security_deposit': str(product.security_deposit),
                'total_payable': str(total_amount),
            }
        })
    except Exception as e:
        import traceback
        print("RAZORPAY ORDER CREATION ERROR:")
        traceback.print_exc()
        return JsonResponse({'error': f'Razorpay error: {str(e)}'}, status=500)

    # Store minimal info in session so verify_payment can retrieve it
    request.session['rzp_product_id']      = product_id
    request.session['rzp_rental_days']     = rental_days
    request.session['rzp_order_id']        = razorpay_order['id']
    request.session['rzp_amount']          = str(total_amount)
    request.session.modified = True

    return JsonResponse({
        'order_id':  razorpay_order['id'],
        'amount':    amount_paise,
        'currency':  'INR',
        'key_id':    settings.RAZORPAY_KEY_ID,
    })

# ─────────────────────────────────────────────────────────────────────────────
# Razorpay: Verify Payment  (called via AJAX after checkout popup succeeds)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def verify_payment(request, product_id):
    """
    POST /product/<id>/verify-payment/
    Receives razorpay_payment_id, razorpay_order_id, razorpay_signature.
    Verifies HMAC-SHA256 signature → saves RentalOrder + RazorpayPayment.
    Returns { success, redirect_url } as JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    product = get_object_or_404(Clothing, id=product_id, is_available=True)

    try:
        body           = json.loads(request.body)
        payment_id     = body.get('razorpay_payment_id', '')
        order_id       = body.get('razorpay_order_id', '')
        signature      = body.get('razorpay_signature', '')
        start_date_str = body.get('start_date', '')
        rental_days    = int(body.get('rental_days', request.session.get('rzp_rental_days', 1)))
        # Address fields bundled from the frontend form
        full_name    = body.get('full_name', '')
        phone_number = body.get('phone_number', '')
        address_line = body.get('address_line', '')
        city         = body.get('city', '')
        pincode      = body.get('pincode', '')
        size         = body.get('size', product.size)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # ── 1. Signature verification ────────────────────────────────────────────
    key_secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
    msg        = f"{order_id}|{payment_id}".encode('utf-8')
    expected   = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return JsonResponse({'error': 'Payment verification failed. Invalid signature.'}, status=400)

    # ── 2. Parse dates ───────────────────────────────────────────────────────
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date   = start_date + timedelta(days=rental_days - 1)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # ── 3. Overlap check ─────────────────────────────────────────────────────
    overlaps = RentalOrder.objects.filter(
        product=product, status='confirmed'
    ).filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    )
    if overlaps.exists():
        return JsonResponse({'error': 'Product already booked for these dates.'}, status=409)

    # ── 4. Save address ──────────────────────────────────────────────────────
    address = UserAddress.objects.create(
        user         = request.user,
        full_name    = full_name,
        phone_number = phone_number,
        address_line = address_line,
        city         = city,
        pincode      = pincode,
    )

    # ── 5. Calculate amounts ─────────────────────────────────────────────────
    price_per_day = product.price_per_day
    deposit       = product.security_deposit
    rent_total    = price_per_day * rental_days
    total_amount  = rent_total + deposit

    # ── 6. Create RentalOrder ────────────────────────────────────────────────
    try:
        rental_order = RentalOrder.objects.create(
            user          = request.user,
            product       = product,
            start_date    = start_date,
            end_date      = end_date,
            rental_days   = rental_days,
            price_per_day = price_per_day,
            deposit       = deposit,
            total_amount  = total_amount,
            payment_method = 'upi',      # Razorpay covers UPI/Card/Netbanking
            address       = address,
            status        = 'confirmed',
            deposit_refund_status = 'pending',
            size          = size,
            tracking_status = 1,
        )
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # ── 7. Save RazorpayPayment ──────────────────────────────────────────────
    RazorpayPayment.objects.create(
        order               = rental_order,
        razorpay_order_id   = order_id,
        razorpay_payment_id = payment_id,
        razorpay_signature  = signature,
        amount              = total_amount,
        currency            = 'INR',
        is_verified         = True,
    )

    # Clear session data
    for key in ('rzp_product_id', 'rzp_rental_days', 'rzp_order_id', 'rzp_amount'):
        request.session.pop(key, None)

    redirect_url = f'/order/{rental_order.id}/success/'
    return JsonResponse({'success': True, 'redirect_url': redirect_url})

# ─────────────────────────────────────────────────────────────────────────────
# Place Order (COD / legacy form POST)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def place_order(request, product_id):
    """Handles the traditional form POST (COD only). UPI/Card go through verify_payment."""
    product = get_object_or_404(Clothing, id=product_id, is_available=True)

    if request.method == 'POST':
        # --- Validate Address ---
        address_form = AddressForm(request.POST)
        if not address_form.is_valid():
            messages.error(request, 'Please provide a valid delivery address.')
            return redirect('payment_page', product_id=product_id)

        address = address_form.save(commit=False)
        address.user = request.user
        address.save()

        # --- Parse Rental Dates ---
        try:
            rental_days    = int(request.POST.get('rental_days', 0))
            start_date_str = request.POST.get('start_date')
            if not start_date_str:
                messages.error(request, 'Please select a start date.')
                return redirect('payment_page', product_id=product_id)
            start_date = date.fromisoformat(start_date_str)
            end_date   = start_date + timedelta(days=rental_days - 1)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rental duration or date format.')
            return redirect('payment_page', product_id=product_id)

        if rental_days < 1:
            messages.error(request, 'Minimum rental duration is 1 day.')
            return redirect('payment_page', product_id=product_id)

        # --- Overlap Check ---
        overlaps = RentalOrder.objects.filter(
            product=product, status='confirmed'
        ).filter(
            Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
        )
        if overlaps.exists():
            messages.error(request, 'This product is already booked for the selected dates.')
            return redirect('payment_page', product_id=product_id)

        # --- Payment Method ---
        payment_method = request.POST.get('payment_method', 'cod')
        if payment_method not in ['upi', 'card', 'cod']:
            messages.error(request, 'Please select a valid payment method.')
            return redirect('payment_page', product_id=product_id)
            
        size = request.POST.get('size', product.size)

        # Only COD is handled here; Razorpay flows go via verify_payment
        if payment_method != 'cod':
            messages.error(request, 'Please complete payment via Razorpay.')
            return redirect('payment_page', product_id=product_id)

        # --- Calculate ---
        price_per_day = product.price_per_day
        deposit       = product.security_deposit
        rent_total    = price_per_day * rental_days
        total_amount  = rent_total + deposit

        # --- Save Order ---
        try:
            order = RentalOrder.objects.create(
                user          = request.user,
                product       = product,
                start_date    = start_date,
                end_date      = end_date,
                rental_days   = rental_days,
                price_per_day = price_per_day,
                deposit       = deposit,
                total_amount  = total_amount,
                payment_method = payment_method,
                address       = address,
                status        = 'confirmed',
                deposit_refund_status = 'pending',
                size          = size,
                tracking_status = 1,
            )
            messages.success(request, f'Order placed successfully for {product.title}!')
            return render(request, 'order_success.html', {'order': order})
        except ValidationError as e:
            messages.error(request, f'Validation Error: {e.message}')
            return redirect('payment_page', product_id=product_id)
        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')
            return redirect('payment_page', product_id=product_id)

    return redirect('payment_page', product_id=product_id)

# ─────────────────────────────────────────────────────────────────────────────
# Order Success & My Orders
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def order_success(request, order_id):
    order = get_object_or_404(RentalOrder, id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})

@login_required
def my_orders(request):
    orders = RentalOrder.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'my_orders.html', {'orders': orders})

@login_required
def cancel_order(request, order_id):
    """Cancels a confirmed order and refunds the total amount to the user's wallet."""
    order = get_object_or_404(RentalOrder, id=order_id, user=request.user)
    
    if order.status != 'confirmed':
        return JsonResponse({'error': f'Order cannot be cancelled. Current status: {order.status}'}, status=400)
    
    try:
        with transaction.atomic():
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            # Refund to Wallet
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += order.total_amount
            wallet.save()
            
            # Record Transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='refund',
                amount=order.total_amount,
                status='completed',
                description=f'Refund for Cancelled Order #{order.id}: {order.product.title}'
            )
            
        return JsonResponse({'success': True, 'message': 'Order cancelled and refund processed.'})
    except Exception as e:
        return JsonResponse({'error': f'Refund failed: {str(e)}'}, status=500)

# ─────────────────────────────────────────────────────────────────────────────
# Cart Views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Clothing, id=product_id)
        size = request.POST.get('size')
        if not size:
            messages.error(request, 'Please select a size.')
            return redirect('product_detail', id=product_id)
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product=product, size=size
        )
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
            messages.info(request, f'Increased quantity for {product.title} ({size}) in your cart.')
        else:
            # Set default rental start date (tomorrow)
            cart_item.start_date = date.today() + timedelta(days=1)
            cart_item.rental_days = 4  # Default 4 days
            cart_item.save()
            messages.success(request, f'Added {product.title} ({size}) to your cart.')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': sum(item.quantity for item in cart.items.all()),
                'message': f'Added {product.title} to your bag.'
            })
        
        return redirect('cart_view')
    return redirect('product_detail', id=product_id)

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    
    # Ensure items have a start_date if not set (for existing items)
    for item in items:
        if not item.start_date:
            item.start_date = date.today() + timedelta(days=1)
            item.save()

    subtotal = sum(item.get_total_price for item in items)
    deposit_total = sum(item.get_deposit_total for item in items)
    grand_total = subtotal + deposit_total
    
    context = {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'deposit_total': deposit_total,
        'total': grand_total,
    }
    return render(request, 'cart.html', context)

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        try:
            start_date_str = request.POST.get('start_date')
            rental_days = request.POST.get('rental_days')
            quantity = request.POST.get('quantity')
            
            if start_date_str:
                item.start_date = date.fromisoformat(start_date_str)
            
            if rental_days:
                item.rental_days = max(1, int(rental_days))
                
            if quantity:
                item.quantity = max(1, int(quantity))
            
            item.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                cart = item.cart
                items = cart.items.all()
                subtotal = sum(i.get_total_price for i in items)
                deposit_total = sum(i.get_deposit_total for i in items)
                total = subtotal + deposit_total
                
                return JsonResponse({
                    'success': True,
                    'cart_count': sum(i.quantity for i in items),
                    'item_subtotal': float(item.get_total_price + item.get_deposit_total),
                    'bag_subtotal': float(subtotal),
                    'bag_deposit': float(deposit_total),
                    'bag_total': float(total),
                    'message': 'Cart updated.'
                })
            
            messages.success(request, f'Updated {item.product.title}.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid input.')
            
    return redirect('cart_view')

@login_required
def remove_from_cart(request, item_id):
    cart = Cart.objects.get(user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_title = item.product.title
    item.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': sum(i.quantity for i in cart.items.all()),
            'message': f'Removed {product_title} from your bag.'
        })
        
    messages.success(request, f'Removed {product_title} from your cart.')
    return redirect('cart_view')

@login_required
def checkout_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    
    if not items:
        messages.warning(request, "Your bag is empty. Please add some pieces to proceed.")
        return redirect('browse')

    subtotal = sum(item.get_total_price for item in items)
    deposit_total = sum(item.get_deposit_total for item in items)
    grand_total = subtotal + deposit_total
    
    # Get last used address for pre-filling
    last_address = UserAddress.objects.filter(user=request.user).order_by('-created_at').first()
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'deposit_total': deposit_total,
        'total': grand_total,
        'last_address': last_address,
        'user': request.user,
    }
    return render(request, 'checkout.html', context)

# ── Checkout Payment Logic ──────────────────────────────────────────────────

@login_required
def create_payment_order(request):
    """Creates a Razorpay order for the total cart amount."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    if not items:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    subtotal = sum(item.get_total_price for item in items)
    deposit_total = sum(item.get_deposit_total for item in items)
    total_amount = float(subtotal + deposit_total)
    
    amount_paise = int(total_amount * 100)
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create({
        'amount':   amount_paise,
        'currency': 'INR',
        'payment_capture': 1
    })

    return JsonResponse({
        'order_id':  razorpay_order['id'],
        'amount':    amount_paise,
        'currency':  'INR',
        'key_id':    settings.RAZORPAY_KEY_ID,
    })

@login_required
def checkout_verify_payment(request):
    """Verifies Razorpay signature and creates RentalOrders for all cart items."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
        payment_id = body.get('razorpay_payment_id', '')
        order_id   = body.get('razorpay_order_id', '')
        signature  = body.get('razorpay_signature', '')
        
        # Address info
        address_data = body.get('address', {})
        full_name    = address_data.get('full_name')
        phone        = address_data.get('phone')
        address_line = address_data.get('address')
        city         = address_data.get('city')
        pincode      = address_data.get('pincode')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Verify signature
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
    except Exception:
        return JsonResponse({'error': 'Payment verification failed'}, status=400)

    # Payment successful - Create Orders
    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()
    
    address = UserAddress.objects.create(
        user=request.user,
        full_name=full_name,
        phone_number=phone,
        address_line=address_line,
        city=city,
        pincode=pincode
    )

    for item in items:
        end_date = item.start_date + timedelta(days=item.rental_days - 1)
        order = RentalOrder.objects.create(
            user=request.user,
            product=item.product,
            start_date=item.start_date,
            end_date=end_date,
            rental_days=item.rental_days,
            price_per_day=item.product.price_per_day,
            deposit=item.product.security_deposit,
            total_amount=item.get_total_price + item.get_deposit_total,
            payment_method='card',
            address=address,
            status='confirmed',
            size=item.size
        )
        
        # Create RazorpayPayment record for internal tracking
        RazorpayPayment.objects.create(
            order=order,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
            amount=order.total_amount,
            is_verified=True
        )

    # Store order IDs for success page
    request.session['last_checkout_orders'] = [o.id for o in RentalOrder.objects.filter(razorpay_payment__razorpay_order_id=order_id)]
    
    # Clear Cart
    items.delete()
    
    return JsonResponse({'success': True, 'redirect_url': '/checkout/success/'})

@login_required
def wallet_payment(request):
    """Handles payment via UserProfile.wallet_balance."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
        address_data = body.get('address', {})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()
    if not items:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    subtotal = sum(item.get_total_price for item in items)
    deposit_total = sum(item.get_deposit_total for item in items)
    total_amount = subtotal + deposit_total

    wallet = request.user.wallet
    if wallet.balance < total_amount:
        return JsonResponse({'error': 'Insufficient wallet balance.'}, status=400)

    # Deduct balance
    wallet.balance -= total_amount
    wallet.save()

    # Create Transaction Record
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='payment',
        amount=total_amount,
        status='completed',
        description=f'Rental Checkout'
    )

    # Create Orders
    address = UserAddress.objects.create(
        user=request.user,
        full_name=address_data.get('full_name'),
        phone_number=address_data.get('phone'),
        address_line=address_data.get('address'),
        city=address_data.get('city'),
        pincode=address_data.get('pincode')
    )

    created_order_ids = []
    for item in items:
        end_date = item.start_date + timedelta(days=item.rental_days - 1)
        order = RentalOrder.objects.create(
            user=request.user,
            product=item.product,
            start_date=item.start_date,
            end_date=end_date,
            rental_days=item.rental_days,
            price_per_day=item.product.price_per_day,
            deposit=item.product.security_deposit,
            total_amount=item.get_total_price + item.get_deposit_total,
            payment_method='wallet',
            address=address,
            status='confirmed',
            size=item.size
        )
        created_order_ids.append(order.id)

    # Store IDs for success page
    request.session['last_checkout_orders'] = created_order_ids

    # Clear Cart
    items.delete()

    return JsonResponse({'success': True, 'redirect_url': '/checkout/success/'})

@login_required
def checkout_success_view(request):
    """Celebratory success page for cart-based checkout."""
    order_ids = request.session.get('last_checkout_orders', [])
    if not order_ids:
        return redirect('my_orders')
    
    orders = RentalOrder.objects.filter(id__in=order_ids, user=request.user)
    if not orders.exists():
        return redirect('my_orders')
        
    total_paid = sum(o.total_amount for o in orders)
    payment_method = orders.first().payment_method
    
    context = {
        'orders': orders,
        'total_paid': total_paid,
        'payment_method': payment_method,
    }
    return render(request, 'checkout_success.html', context)

@login_required
def wallet_dashboard(request):
    """View for user's wallet and transactions."""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()
    return render(request, 'wallet.html', {
        'wallet': wallet,
        'transactions': transactions
    })

@login_required
def add_funds(request):
    """Creates Razorpay order for wallet deposit."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        body = json.loads(request.body)
        amount = float(body.get('amount', 0))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)
    
    if amount < 10:
        return JsonResponse({'error': 'Minimum deposit is ₹10'}, status=400)
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    data = {
        'amount': int(amount * 100),
        'currency': 'INR',
        'payment_capture': '1'
    }
    rzp_order = client.order.create(data=data)
    
    WalletTransaction.objects.create(
        wallet=request.user.wallet,
        transaction_type='deposit',
        amount=amount,
        status='pending',
        razorpay_order_id=rzp_order['id'],
        description='Wallet Deposit'
    )
    
    return JsonResponse({
        'order_id': rzp_order['id'],
        'amount': rzp_order['amount'],
        'key_id': settings.RAZORPAY_KEY_ID
    })

@login_required
def verify_wallet_payment(request):
    """Verifies deposit and updates balance."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    body = json.loads(request.body)
    payment_id = body.get('razorpay_payment_id')
    order_id = body.get('razorpay_order_id')
    signature = body.get('razorpay_signature')
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
        tx = WalletTransaction.objects.get(razorpay_order_id=order_id, wallet__user=request.user)
        if tx.status == 'pending':
            tx.status = 'completed'
            tx.razorpay_payment_id = payment_id
            tx.save()
            
            wallet = tx.wallet
            wallet.balance += tx.amount
            wallet.save()
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Processed'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def withdraw_funds(request):
    """Handles withdrawal requests."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        body = json.loads(request.body)
        amount = float(body.get('amount', 0))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)
    
    if amount < 100:
        return JsonResponse({'error': 'Min ₹100'}, status=400)
    
    wallet = request.user.wallet
    if wallet.balance < amount:
        return JsonResponse({'error': 'Insufficient balance'}, status=400)
    
    wallet.balance -= amount
    wallet.save()
    
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='withdraw',
        amount=amount,
        status='pending',
        description='Wallet Withdrawal Request'
    )
    return JsonResponse({'success': True})

# ─────────────────────────────────────────────────────────────────────────────
# Admin / Management Operations
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    """Luxury management interface for the site owner."""
    if not request.user.userprofile.is_owner:
        messages.error(request, 'Access Denied.')
        return redirect('home')
    
    orders = RentalOrder.objects.all().order_by('-order_date')
    pending_withdrawals = WalletTransaction.objects.filter(
        transaction_type='withdraw', 
        status='pending'
    ).order_by('-created_at')
    
    return render(request, 'admin_dashboard.html', {
        'orders': orders,
        'pending_withdrawals': pending_withdrawals
    })

@login_required
def update_order_status(request, order_id):
    """Admin endpoint to move order through the rental lifecycle."""
    if not request.user.userprofile.is_owner:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        body = json.loads(request.body)
        new_status = body.get('status')
        order = get_object_or_404(RentalOrder, id=order_id)
        
        if new_status not in [s[0] for s in ORDER_STATUS_CHOICES]:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        with transaction.atomic():
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Logic: If marked as 'returned', AUTO-REFUND security deposit to Wallet
            if new_status == 'returned' and order.deposit_refund_status == 'pending':
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
                wallet.balance += order.deposit
                wallet.save()
                
                order.deposit_refund_status = 'refunded'
                order.save()
                
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    amount=order.deposit,
                    status='completed',
                    description=f'Security Deposit Refund for Order #{order.id}'
                )
            
        return JsonResponse({'success': True, 'new_status': new_status})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def approve_withdrawal(request, tx_id):
    """Admin endpoint to finalize a pending user payout."""
    if not request.user.userprofile.is_owner:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    tx = get_object_or_404(WalletTransaction, id=tx_id, transaction_type='withdraw')
    if tx.status == 'pending':
        tx.status = 'completed'
        tx.save()
        messages.success(request, f'Withdrawal of ₹{tx.amount} approved for {tx.wallet.user.username}.')
    
    return redirect('admin_dashboard')
