from django.urls import path
from . import views
from .views import pay, check_payment_status, payment_return

urlpatterns = [
    path('pay/', views.pay, name='pay'),
    path('check-status/', check_payment_status, name='check_status'),
    path('payment-return/', payment_return, name='payment_return'),
]