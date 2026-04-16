from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('browse/', views.browse, name='browse'),
    path('collections/', views.collections, name='collections'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # Payment
    path('product/<int:product_id>/payment/', views.payment_page, name='payment_page'),
    path('product/<int:product_id>/place-order/', views.place_order, name='place_order'),
    path('order/<int:order_id>/success/', views.order_success, name='order_success'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('my-orders/', views.my_orders, name='my_orders'),

    # Razorpay API endpoints (JSON)
    path('product/<int:product_id>/create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('product/<int:product_id>/verify-payment/', views.verify_payment, name='verify_payment'),

    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/create-razorpay-order/', views.create_payment_order, name='checkout_create_razorpay_order'),
    path('checkout/verify-payment/', views.checkout_verify_payment, name='checkout_verify_payment'),
    path('checkout/wallet-payment/', views.wallet_payment, name='checkout_wallet_payment'),
    path('checkout/success/', views.checkout_success_view, name='checkout_success'),

    # Wallet System
    path('wallet/', views.wallet_dashboard, name='wallet_dashboard'),
    path('wallet/add-funds/', views.add_funds, name='add_funds'),
    path('wallet/verify-payment/', views.verify_wallet_payment, name='verify_wallet_payment'),
    path('wallet/withdraw/', views.withdraw_funds, name='withdraw_funds'),

    # Admin / Management
    path('manage/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('manage/withdrawal/<int:tx_id>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
]