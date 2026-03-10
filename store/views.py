# Create your views here.

from django.shortcuts import render,get_object_or_404
from .models import Clothing,Category


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

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    clothes = Clothing.objects.filter(category=category, is_available=True)

    return render(request, 'browse.html', {
        'clothes': clothes,
        'selected_category': category
    })