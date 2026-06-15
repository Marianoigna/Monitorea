import requests

ACCESS_TOKEN = "APP_USR-1927667665037758-061120-14dec94107a416966544c6b77d9665e0-3468655152"
NOTIFICATION_URL = "https://pasarela-prueba-a-mp.onrender.com/suscripciones/webhook/"

ids = {
    "mensual": "4505e087517f47c7ba64b2ed7daf7cae",
    "anual":   "acff5fd3356549749c12f38cdb29f1f3",
}

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

for tipo, plan_id in ids.items():
    url = f"https://api.mercadopago.com/preapproval_plan/{plan_id}"
    body = {"notification_url": NOTIFICATION_URL}
    resp = requests.put(url, headers=headers, json=body, timeout=10)
    print(f"\n=== {tipo.upper()} ({plan_id}) ===")
    print("HTTP Status:", resp.status_code)
    print("Respuesta completa:", resp.json())  # ← esto muestra el error real

