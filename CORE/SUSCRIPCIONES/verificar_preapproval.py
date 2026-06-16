import requests

ACCESS_TOKEN = "APP_USR-1927667665037758-061120-14dec94107a416966544c6b77d9665e0-3468655152"

# IDs de preapproval que aparecen en tus logs de Render
PREAPPROVAL_IDS = [
    "d6f6974c4e914d75aec70a3711c6b3e2",
    "07af00d98529433da31d2500e635e5eb",
]

headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

for pid in PREAPPROVAL_IDS:
    print(f"\n===== PREAPPROVAL {pid} =====")
    r = requests.get(
        f"https://api.mercadopago.com/preapproval/{pid}",
        headers=headers,
        timeout=10,
    )
    print("HTTP:", r.status_code)
    data = r.json()
    # Los campos que importan:
    print("status:            ", data.get("status"))
    print("external_reference:", repr(data.get("external_reference")))
    print("payer_email:       ", data.get("payer_email"))
    print("payer_id:          ", data.get("payer_id"))
    print("preapproval_plan_id:", data.get("preapproval_plan_id"))
    print("reason:            ", data.get("reason"))
    print("init_point existe: ", bool(data.get("init_point")))
