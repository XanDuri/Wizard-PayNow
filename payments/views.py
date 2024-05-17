import requests
from django.shortcuts import render, redirect
from django.conf import settings
import hmac
import hashlib
import base64
import json
import uuid

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
            "externalId": "unique_order_id",
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
            payment_url = response.json().get('redirectUrl')
            return redirect(payment_url)  # Przekierowuje użytkownika do Paynow
        else:
            error_message = response.text  # Tekst odpowiedzi, który może zawierać informacje o błędzie
            return render(request, 'payments/pay.html', {'error': 'Nie można zainicjować płatności: ' + error_message})

