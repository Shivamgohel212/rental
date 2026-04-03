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

from .forms import AddressForm, LoginForm, UserRegistrationForm
from .models import Clothing, Category, RentalOrder, RazorpayPayment, UserAddress

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
    return render(request, 'browse.html', {'clothes': clothes})

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
    if gender:
        clothes = clothes.filter(gender=gender)
    return render(request, 'browse.html', {
        'clothes': clothes,
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