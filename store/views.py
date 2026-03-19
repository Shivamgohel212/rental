from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import ValidationError
from .models import Clothing, Category, RentalOrder, UserAddress
from .forms import UserRegistrationForm, LoginForm, AddressForm
from datetime import date, timedelta

MIN_RENTAL_DAYS = 1
MAX_RENTAL_DAYS = 30

# --------------- Public Views ---------------

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
        'selected_category': category
    })

# --------------- Auth Views ---------------

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

# --------------- Payment Views ---------------

MIN_RENTAL_DAYS = 1
MAX_RENTAL_DAYS = 30

@login_required
def payment_page(request, product_id):
    product = get_object_or_404(Clothing, id=product_id, is_available=True)
    # Fetch the last saved address for this user to pre-fill the form
    from .models import UserAddress
    last_address = UserAddress.objects.filter(user=request.user).order_by('-created_at').first()
    
    context = {
        'product': product,
        'min_days': MIN_RENTAL_DAYS,
        'max_days': MAX_RENTAL_DAYS,
        'last_address': last_address,
        'min_rental_days': MIN_RENTAL_DAYS,
        'max_rental_days': MAX_RENTAL_DAYS,
        # Fetch booked dates for this product to show in the UI (optional future enhancement)
        'booked_orders': RentalOrder.objects.filter(product=product, status='confirmed').values('start_date', 'end_date')
    }
    return render(request, 'payment.html', context)


@login_required
def place_order(request, product_id):
    product = get_object_or_404(Clothing, id=product_id, is_available=True)

    if request.method == 'POST':
        # --- Validate Address ---
        address_form = AddressForm(request.POST)
        if not address_form.is_valid():
            messages.error(request, 'Please provide valid delivery address.')
            return redirect('payment_page', product_id=product_id)
        
        address = address_form.save(commit=False)
        address.user = request.user
        address.save()

        # --- Parse and Validate Rental Dates ---
        try:
            rental_days = int(request.POST.get('rental_days', 0))
            start_date_str = request.POST.get('start_date')
            if not start_date_str:
                messages.error(request, 'Please select a start date.')
                return redirect('payment_page', product_id=product_id)
            
            start_date = date.fromisoformat(start_date_str)
            # Duration of 3 days means: day 1, day 2, day 3. End date is start + 2 days.
            end_date = start_date + timedelta(days=rental_days - 1)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rental duration or date format.')
            return redirect('payment_page', product_id=product_id)

        if rental_days < 1:
            messages.error(request, 'Minimum rental duration is 1 day.')
            return redirect('payment_page', product_id=product_id)
        
        # --- Final Overlap Check ---
        # A booking overlaps if (start1 <= end2) AND (end1 >= start2)
        overlaps = RentalOrder.objects.filter(
            product=product,
            status='confirmed'
        ).filter(
            Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
        )
        
        if overlaps.exists():
            messages.error(request, 'This product is already booked for the selected dates.')
            return redirect('payment_page', product_id=product_id)

        # --- Validate payment method ---
        payment_method = request.POST.get('payment_method', 'cod')
        valid_methods = ['upi', 'card', 'cod']
        if payment_method not in valid_methods:
            messages.error(request, 'Please select a valid payment method.')
            return redirect('payment_page', product_id=product_id)

        # --- Calculate amounts ---
        price_per_day = product.price_per_day
        deposit = product.security_deposit
        rent_total = price_per_day * rental_days
        total_amount = rent_total + deposit

        # --- Save order ---
        try:
            order = RentalOrder.objects.create(
                user=request.user,
                product=product,
                start_date=start_date,
                end_date=end_date,
                rental_days=rental_days,
                price_per_day=price_per_day,
                deposit=deposit,
                total_amount=total_amount,
                payment_method=payment_method,
                address=address,
                status='confirmed',
            )
            messages.success(request, f'Order placed successfully for {product.title}!')
            return render(request, 'order_success.html', {'order': order})
        except ValidationError as e:
            messages.error(request, f'Validation Error: {e.message}')
            return redirect('payment_page', product_id=product_id)
        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')
            return redirect('payment_page', product_id=product_id)

        return redirect('order_success', order_id=order.id)

    return redirect('payment_page', product_id=product_id)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(RentalOrder, id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = RentalOrder.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'my_orders.html', {'orders': orders})