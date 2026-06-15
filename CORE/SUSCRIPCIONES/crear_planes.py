import requests

ACCESS_TOKEN = "APP_USR-1927667665037758-061120-14dec94107a416966544c6b77d9665e0-3468655152"
NOTIFICATION_URL = "https://pasarela-prueba-a-mp.onrender.com/suscripciones/webhook/"
BACK_URL = "https://pasarela-prueba-a-mp.onrender.com/suscripciones/pago-exitoso/"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

planes = {
    "mensual": {"frequency": 1,  "frequency_type": "months", "transaction_amount": 30000.0},
    "anual":   {"frequency": 12, "frequency_type": "months", "transaction_amount": 300000.0},
}

for tipo, recurring in planes.items():
    body = {
        "reason": f"Monitorea Premium {tipo.capitalize()}",
        "auto_recurring": {
            "frequency": recurring["frequency"],
            "frequency_type": recurring["frequency_type"],
            "transaction_amount": recurring["transaction_amount"],
            "currency_id": "ARS",
        },
        "back_url": BACK_URL,
        "notification_url": NOTIFICATION_URL,
    }
    resp = requests.post(
        "https://api.mercadopago.com/preapproval_plan",
        headers=headers,
        json=body,
        timeout=10,
    )
    print(f"\n=== NUEVO PLAN {tipo.upper()} ===")
    print("HTTP Status:", resp.status_code)
    data = resp.json()
    print("ID nuevo:", data.get("id"))
    print("notification_url:", data.get("notification_url"))
    print("init_point:", data.get("init_point"))
    if resp.status_code != 201:
        print("Respuesta completa (error):", data)