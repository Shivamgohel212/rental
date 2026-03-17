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
    path('my-orders/', views.my_orders, name='my_orders'),
]