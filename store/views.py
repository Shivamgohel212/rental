# Create your views here.

from django.shortcuts import render
from .models import Clothing


def home(request):
    featured = Clothing.objects.filter(
        is_available=True,
        is_featured=True
    )[:3]

    return render(request, 'home.html', {'featured': featured})

def browse(request):
    clothes = Clothing.objects.filter(is_available=True)
    return render(request, 'browse.html', {'clothes': clothes})

def collections(request):
    return render(request, 'collections.html')

def how_it_works(request):
    return render(request, 'how_it_works.html')