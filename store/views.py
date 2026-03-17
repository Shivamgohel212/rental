from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Clothing, Category, RentalOrder
from .forms import UserRegistrationForm, LoginForm

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
            phone = form.cleaned_data.get('phone')
            if phone:
                user.userprofile.phone = phone
                user.userprofile.save()
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
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
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
    context = {
        'product': product,
        'min_days': MIN_RENTAL_DAYS,
        'max_days': MAX_RENTAL_DAYS,
    }
    return render(request, 'payment.html', context)


@login_required
def place_order(request, product_id):
    product = get_object_or_404(Clothing, id=product_id, is_available=True)

    if request.method == 'POST':
        # --- Validate rental days ---
        try:
            rental_days = int(request.POST.get('rental_days', 0))
        except (ValueError, TypeError):
            messages.error(request, 'Invalid number of rental days.')
            return redirect('payment_page', product_id=product_id)

        if rental_days < MIN_RENTAL_DAYS:
            messages.error(request, f'Minimum rental duration is {MIN_RENTAL_DAYS} day(s).')
            return redirect('payment_page', product_id=product_id)
        if rental_days > MAX_RENTAL_DAYS:
            messages.error(request, f'Maximum rental duration is {MAX_RENTAL_DAYS} days.')
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
        order = RentalOrder.objects.create(
            user=request.user,
            product=product,
            rental_days=rental_days,
            price_per_day=price_per_day,
            deposit=deposit,
            total_amount=total_amount,
            payment_method=payment_method,
            status='confirmed',
        )

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