from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import Clothing, Category
from .forms import UserRegistrationForm, LoginForm

def home(request):
    featured = Clothing.objects.filter(
        is_available=True,
        is_featured=True
    )[:]
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

    clothes = Clothing.objects.filter(
        category=category,
        is_available=True
    )

    gender = request.GET.get('gender')

    if gender:
        clothes = clothes.filter(gender=gender)

    return render(request, 'browse.html', {
        'clothes': clothes,
        'selected_category': category
    })

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Save the phone number to the created UserProfile
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
            
            # Django authenticate() normally takes a username. We need to find the user by email.
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