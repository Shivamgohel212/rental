# Create your views here.

from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def browse(request):
    return render(request, 'browse.html')

def collections(request):
    return render(request, 'collections.html')

def how_it_works(request):
    return render(request, 'how_it_works.html')