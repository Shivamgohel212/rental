from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# --- Choice Constants ---
BOOKING_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Cancelled', 'Cancelled'),
    ('Returned', 'Returned'),
]

PAYMENT_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Completed', 'Completed'),
    ('Failed', 'Failed'),
]

ORDER_STATUS_CHOICES = [
    ('confirmed', 'Confirmed'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('returned', 'Returned'),
    ('cancelled', 'Cancelled'),
]

TRANSACTION_TYPE_CHOICES = [
    ('deposit', 'Deposit'),
    ('withdraw', 'Withdraw'),
    ('payment', 'Rental Payment'),
    ('refund', 'Refund'),
]

TRANSACTION_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
]

DEPOSIT_REFUND_STATUS_CHOICES = [
    ('pending', 'Pending Refund'),
    ('refunded', 'Refunded'),
    ('withheld', 'Withheld'),
]

PAYMENT_METHOD_CHOICES = [
    ('upi', 'UPI'),
    ('card', 'Card'),
    ('cod', 'Cash on Delivery'),
    ('wallet', 'Wallet'),
]

GENDER_CHOICES = (
    ('men', 'Men'),
    ('women', 'Women'),
)

# --- Models ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_owner = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type.title()} - ₹{self.amount} ({self.status})"

@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_wallet(sender, instance, **kwargs):
    if hasattr(instance, 'wallet'):
        instance.wallet.save()

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='categories/')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Clothing(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    size = models.CharField(max_length=20)
    brand = models.CharField(max_length=100)
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='clothing/')
    stock = models.IntegerField(default=1)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_currently_booked(self):
        today = timezone.now().date()
        return self.rental_orders.filter(
            status='confirmed',
            start_date__lte=today,
            end_date__gte=today
        ).exists()

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    clothing = models.ForeignKey(Clothing, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='Pending')
    booked_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be greater than start date.")

        overlapping_bookings = Booking.objects.filter(clothing=self.clothing).filter(
            Q(start_date__lt=self.end_date) & Q(end_date__gt=self.start_date)
        )
        if self.pk:
            overlapping_bookings = overlapping_bookings.exclude(pk=self.pk)
        if overlapping_bookings.exists():
            raise ValidationError("This clothing is already booked for selected dates.")

        self.total_days = (self.end_date - self.start_date).days
        self.total_price = self.total_days * self.clothing.price_per_day
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.clothing.title}"

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_id

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    clothing = models.ForeignKey(Clothing, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating}"

class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"

class RentalOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rental_orders')
    product = models.ForeignKey(Clothing, on_delete=models.CASCADE, related_name='rental_orders')
    
    start_date = models.DateField()
    end_date = models.DateField()
    rental_days = models.PositiveIntegerField()
    
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    deposit = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cod')
    address = models.ForeignKey(UserAddress, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='confirmed')
    deposit_refund_status = models.CharField(max_length=20, choices=DEPOSIT_REFUND_STATUS_CHOICES, default='pending')
    razorpay_refund_id = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=10, blank=True, null=True)
    tracking_status = models.IntegerField(default=1) # 1: Ordered, 2: Packed, 3: Shipped, 4: On Way, 5: Arrived
    order_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-order_date']

    def clean(self):
        # Overlap validation logic
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError("End date must be greater than start date.")
            
            # Check for overlapping CONFIRMED orders
            overlaps = RentalOrder.objects.filter(
                product=self.product,
                status='confirmed'
            ).filter(
                Q(start_date__lte=self.end_date) & Q(end_date__gte=self.start_date)
            )
            
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            
            if overlaps.exists():
                raise ValidationError("This product is already booked for the selected dates.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def get_rent_total(self):
        return self.price_per_day * self.rental_days

    def __str__(self):
        return f"Order #{self.pk} – {self.user.username} – {self.product.title} ({self.start_date} to {self.end_date})"


class RazorpayPayment(models.Model):
    """Stores Razorpay transaction details for every online payment."""
    order         = models.OneToOneField(RentalOrder, on_delete=models.CASCADE, related_name='razorpay_payment')
    razorpay_order_id   = models.CharField(max_length=100)          # rzp order id
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)  # after success
    razorpay_signature  = models.CharField(max_length=200, blank=True, null=True)  # for verification
    amount        = models.DecimalField(max_digits=10, decimal_places=2)
    currency      = models.CharField(max_length=10, default='INR')
    is_verified   = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RazorpayPayment – Order #{self.order_id} – {'✓' if self.is_verified else '✗'}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Clothing, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=1)
    # Rental duration fields
    start_date = models.DateField(null=True, blank=True)
    rental_days = models.PositiveIntegerField(default=4)
    
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_total_price(self):
        # Total = (Price Per Day * Rental Days) * Quantity
        return (self.product.price_per_day * self.rental_days) * self.quantity

    @property
    def get_deposit_total(self):
        return self.product.security_deposit * self.quantity

    def __str__(self):
        return f"{self.product.title} ({self.size}) in {self.cart.user.username}'s Cart"