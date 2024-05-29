import requests
from django.shortcuts import render, redirect
from django.conf import settings
from .models import Payment
import hmac
import hashlib
import base64
import json
import uuid

def get_payment_status(payment_id):
    api_url = f"https://api.sandbox.paynow.pl/v1/payments/{payment_id}/status"
    headers = {
        'Api-Key': settings.PAYNOW_API_KEY,
        'Signature': settings.PAYNOW_SIGNATURE_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()  # Zwraca JSON z informacjami o statusie
    else:
        return None  # W przypadku błędu zwraca None

def generate_signature(api_secret, body):
    """Generuje podpis zgodnie z dokumentacją Paynow."""
    sorted_body = json.dumps(body, separators=(',', ':'), sort_keys=True).encode('utf-8')
    secret = api_secret.encode('utf-8')
    hashed_object = hmac.new(secret, sorted_body, hashlib.sha256).digest()
    signature = base64.b64encode(hashed_object).decode('utf-8')
    return signature

# Create your views here.
def pay(request):
    if request.method == 'GET':
        return render(request, 'payments/pay.html')

    if request.method == 'POST':
        api_url = "https://api.sandbox.paynow.pl/v1/payments"
        body = {
            "amount": "1000",  # 10 PLN, kwota musi być podana w groszach
            "currency": "PLN",
            "externalId": str(uuid.uuid4()),
            "description": "Opis płatności",
            "buyer": {
                "email": "customer@example.com"
            }
        }
        json_body = json.dumps(body, separators=(',', ':'), sort_keys=True).encode('utf-8')
        signature = generate_signature(settings.PAYNOW_SIGNATURE_KEY, body)

        headers = {
            'Api-Key': settings.PAYNOW_API_KEY,
            'Signature': signature,
            'Content-Type': 'application/json',
            'Idempotency-Key': str(uuid.uuid4())  # Musi być unikalny dla każdej transakcji
        }

        response = requests.post(api_url, data=json_body, headers=headers)
        if response.status_code == 201:
            payment_data = response.json()
            # Tworzenie i zapisywanie obiektu płatności
            Payment.objects.create(
                payment_id=payment_data['paymentId'],
                status='INITIATED',
                amount=float(body['amount']) / 100,  # przeliczenie groszy na złote
                email=body['buyer']['email'],
                description=body['description']
            )
            redirect_url = f'{payment_data["redirectUrl"]}?payment_id={payment_data["paymentId"]}'
            return redirect(payment_data['redirectUrl'])
        else:
            return render(request, 'payments/pay.html', {'error': 'Nie można zainicjować płatności: ' + response.text})

def check_payment_status(request):
    payment_id = request.session.get('payment_id')
    if payment_id:
        status_info = get_payment_status(payment_id)
        if status_info:
            # Aktualizacja obiektu płatności w bazie danych
            payment = Payment.objects.get(payment_id=payment_id)
            payment.status = status_info['status']
            payment.save()
            return render(request, 'payments/status.html', {'status': status_info})
        else:
            return render(request, 'payments/status.html', {'error': 'Nie udało się uzyskać statusu płatności.'})
    else:
        return render(request, 'payments/status.html', {'error': 'Brak identyfikatora płatności w sesji.'})

def payment_return(request):
    payment_id = request.GET.get('paymentId')  # Zmienione z 'payment_id' na 'paymentId'
    payment_status = request.GET.get('paymentStatus')  # Nowy parametr z URL-a

    if payment_id:
        status_info = get_payment_status(payment_id)
        if status_info:
            try:
                payment = Payment.objects.get(payment_id=payment_id)
                payment.status = payment_status  # Użyj bezpośrednio statusu z URL, jeśli jest dostępny
                payment.save()
                return render(request, 'payments/status.html', {'status': status_info})
            except Payment.DoesNotExist:
                return render(request, 'payments/error.html', {'error': 'Płatność nie znaleziona.'})
        else:
            return render(request, 'payments/error.html', {'error': 'Nie udało się uzyskać statusu płatności.'})
    else:
        return render(request, 'payments/error.html', {'error': 'Brak identyfikatora płatności.'})