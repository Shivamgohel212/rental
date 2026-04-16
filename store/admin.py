from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Category, Clothing, Booking,
    Payment, Review, UserAddress, RentalOrder,
    RazorpayPayment, Cart, CartItem
)


# ─────────────────────────────────────────────────────────────────────────────
# Utility: colour-coded status badges
# ─────────────────────────────────────────────────────────────────────────────

def status_badge(value, colour_map):
    """Return a styled HTML badge for a status value."""
    colour = colour_map.get(value, '#6c757d')
    return format_html(
        '<span style="background:{};color:#fff;padding:3px 10px;'
        'border-radius:12px;font-size:0.78rem;font-weight:600;">{}</span>',
        colour, value.title()
    )


# ─────────────────────────────────────────────────────────────────────────────
# RentalOrder
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'product_link', 'size',
        'coloured_status', 'tracking_badge',
        'total_amount', 'payment_method',
        'deposit_refund_status', 'order_date',
    )
    list_filter   = ('status', 'deposit_refund_status', 'payment_method', 'order_date')
    search_fields = ('user__username', 'user__email', 'product__title', 'id')
    readonly_fields = ('order_date',)
    date_hierarchy  = 'order_date'
    list_per_page   = 25
    save_on_top     = True

    fieldsets = (
        ('📦 Order Info', {
            'fields': ('user', 'product', 'status', 'order_date')
        }),
        ('📅 Rental Details', {
            'fields': ('start_date', 'end_date', 'rental_days', 'size')
        }),
        ('💰 Financials', {
            'fields': ('price_per_day', 'deposit', 'total_amount', 'payment_method')
        }),
        ('🔒 Security Deposit', {
            'fields': ('deposit_refund_status', 'razorpay_refund_id')
        }),
        ('🚚 Shipping', {
            'fields': ('address',)
        }),
        ('📡 Tracking', {
            'fields': ('tracking_status',),
            'description': '1=Ordered  2=Packed  3=Shipped  4=On the Way  5=Arrived',
        }),
    )

    @admin.display(description='Product', ordering='product__title')
    def product_link(self, obj):
        return format_html('<b>{}</b>', obj.product.title)

    @admin.display(description='Status')
    def coloured_status(self, obj):
        colours = {'confirmed': '#28a745', 'cancelled': '#dc3545', 'pending': '#fd7e14'}
        return status_badge(obj.status, colours)

    @admin.display(description='Tracking')
    def tracking_badge(self, obj):
        labels = {1: '📦 Ordered', 2: '🎁 Packed', 3: '🚚 Shipped', 4: '🛵 On Way', 5: '🏠 Arrived'}
        colours = {1: '#6c757d', 2: '#17a2b8', 3: '#007bff', 4: '#fd7e14', 5: '#28a745'}
        label = labels.get(obj.tracking_status, str(obj.tracking_status))
        colour = colours.get(obj.tracking_status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:0.78rem;font-weight:600;">{}</span>',
            colour, label
        )


# ─────────────────────────────────────────────────────────────────────────────
# RazorpayPayment
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display    = ('id', 'order', 'razorpay_order_id', 'razorpay_payment_id',
                       'amount', 'currency', 'verified_badge', 'created_at')
    list_filter     = ('is_verified', 'currency')
    search_fields   = ('razorpay_order_id', 'razorpay_payment_id', 'order__id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
                       'amount', 'currency', 'is_verified', 'created_at')
    date_hierarchy  = 'created_at'
    list_per_page   = 25

    @admin.display(description='Verified', boolean=False)
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#28a745;font-weight:700;">✔ Verified</span>')
        return format_html('<span style="color:#dc3545;font-weight:700;">✘ Unverified</span>')


# ─────────────────────────────────────────────────────────────────────────────
# Clothing
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Clothing)
class ClothingAdmin(admin.ModelAdmin):
    list_display   = ('id', 'title', 'category', 'gender', 'size', 'brand',
                      'price_per_day', 'security_deposit', 'stock',
                      'is_available', 'is_featured', 'created_at')
    list_filter    = ('category', 'gender', 'is_available', 'is_featured', 'brand')
    search_fields  = ('title', 'brand', 'description')
    list_editable  = ('is_available', 'is_featured', 'stock')
    list_per_page  = 20
    save_on_top    = True
    date_hierarchy = 'created_at'

    fieldsets = (
        ('📋 Basic Info', {
            'fields': ('owner', 'category', 'title', 'description', 'brand', 'gender', 'size')
        }),
        ('💲 Pricing', {
            'fields': ('price_per_day', 'security_deposit')
        }),
        ('🖼️ Media', {
            'fields': ('image',)
        }),
        ('⚙️ Availability', {
            'fields': ('stock', 'is_available', 'is_featured')
        }),
    )

    @admin.display(description='Available', boolean=True)
    def available_badge(self, obj):
        return obj.is_available

    @admin.display(description='Featured', boolean=True)
    def featured_badge(self, obj):
        return obj.is_featured


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


# ─────────────────────────────────────────────────────────────────────────────
# UserProfile
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'is_owner')
    list_filter   = ('is_owner',)
    search_fields = ('user__username', 'user__email')


# ─────────────────────────────────────────────────────────────────────────────
# UserAddress
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'full_name', 'city', 'pincode', 'phone_number', 'created_at')
    search_fields = ('user__username', 'full_name', 'city', 'pincode')
    list_per_page = 25


# ─────────────────────────────────────────────────────────────────────────────
# Booking
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'clothing', 'start_date', 'end_date',
                     'total_days', 'total_price', 'status', 'booked_at')
    list_filter   = ('status', 'booked_at')
    search_fields = ('user__username', 'clothing__title')
    date_hierarchy = 'booked_at'


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'booking', 'payment_method', 'transaction_id',
                     'amount', 'payment_status', 'paid_at')
    list_filter   = ('payment_status', 'payment_method')
    search_fields = ('transaction_id', 'booking__user__username')
    date_hierarchy = 'paid_at'


# ─────────────────────────────────────────────────────────────────────────────
# Review
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'clothing', 'rating', 'created_at')
    list_filter   = ('rating',)
    search_fields = ('user__username', 'clothing__title', 'comment')
    date_hierarchy = 'created_at'


# ─────────────────────────────────────────────────────────────────────────────
# Cart & CartItem (inline)
# ─────────────────────────────────────────────────────────────────────────────

class CartItemInline(admin.TabularInline):
    model  = CartItem
    extra  = 0
    fields = ('product', 'size', 'quantity', 'rental_days', 'start_date')
    readonly_fields = ('added_at',) if hasattr(CartItem, 'added_at') else ()


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'created_at')
    search_fields = ('user__username',)
    inlines       = [CartItemInline]