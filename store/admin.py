from django.contrib import admin
from .models import UserProfile, Category, Clothing, Booking, Payment, Review, UserAddress, RentalOrder

admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Clothing)
admin.site.register(Booking)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(UserAddress)
admin.site.register(RentalOrder)