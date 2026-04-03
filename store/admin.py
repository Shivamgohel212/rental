from django.contrib import admin
from .models import UserProfile, Category, Clothing, Booking, Payment, Review, UserAddress, RentalOrder, RazorpayPayment


@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display  = ('order', 'razorpay_order_id', 'razorpay_payment_id', 'amount', 'currency', 'is_verified', 'created_at')
    list_filter   = ('is_verified', 'currency')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'amount', 'currency', 'is_verified', 'created_at')


@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'product', 'total_amount', 'deposit', 'status', 'deposit_refund_status', 'order_date')
    list_filter   = ('status', 'deposit_refund_status', 'order_date')
    search_fields = ('user__username', 'product__title', 'id')
    readonly_fields = ('order_date',)
    fieldsets = (
        ('Order Info', {'fields': ('user', 'product', 'status', 'order_date')}),
        ('Rental Details', {'fields': ('start_date', 'end_date', 'rental_days')}),
        ('Financials', {'fields': ('price_per_day', 'deposit', 'total_amount', 'payment_method')}),
        ('Security Deposit', {'fields': ('deposit_refund_status', 'razorpay_refund_id')}),
        ('Shipping', {'fields': ('address',)}),
    )


admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Clothing)
admin.site.register(Booking)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(UserAddress)