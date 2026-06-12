import json
import logging
from datetime import timedelta
from urllib.parse import urlparse

import mercadopago
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@login_required
def planes(request):
    """Página de planes — muestra las opciones de suscripción."""
    return render(request, 'SUSCRIPCIONES/planes.html')


@login_required
def crear_suscripcion(request):
    """
    Crea una pre-aprobación en MercadoPago y redirige al usuario al
    formulario de pago de MP (Checkout Pro).

    Requiere en settings:
      MERCADOPAGO_ACCESS_TOKEN  - token de acceso de la app MP
      MERCADOPAGO_PLAN_ID       - ID del plan de suscripción creado en el panel MP
      MERCADOPAGO_BACK_URL      - URL de retorno tras el pago

    Flujo:
      1. Usuario hace clic en "Activar Premium".
      2. Esta vista crea la suscripción en MP con el email del usuario.
      3. Redirige a init_point (formulario de pago de MP).
      4. MP llama al webhook cuando el pago es aprobado.
    """
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    subscription_data = {
        "preapproval_plan_id": settings.MERCADOPAGO_PLAN_ID,
        "payer_email": request.user.email,
        "back_url": settings.MERCADOPAGO_BACK_URL,
    }

    response = sdk.preapproval().create(subscription_data)

    if response["status"] == 201:
        init_point = response["response"]["init_point"]
        return redirect(init_point)

    logger.error("Error creando suscripción MP: %s", response)
    return redirect('dashboard:dashboard')


@csrf_exempt
@require_POST
def webhook(request):
    """
    Recibe notificaciones de Checkout Pro (tipo 'payment') de MercadoPago.

    Flujo:
      1. MP envía un POST con JSON: {"type": "payment", "data": {"id": "<payment_id>"}, ...}
      2. Se consulta la API de MP para obtener el detalle del pago.
      3. Si status == 'approved':
         - Se busca el CustomUser por payer.email.
         - Se activa is_premium = True y se extiende premium_until 30 días.
         - Se crea o actualiza el objeto Pago vinculado a la Suscripcion del usuario.

    IMPORTANTE: siempre retorna HTTP 200 para que MP no reintente la notificación.
    Para desarrollo local usá ngrok: ngrok http 8000
    """
    # ── 1. Parsear cuerpo ─────────────────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Webhook MP: cuerpo JSON inválido.")
        return HttpResponse(status=200)

    notification_type = data.get("type") or data.get("action", "")

    # Checkout Pro envía type='payment'; ignorar el resto silenciosamente
    if "payment" not in notification_type:
        return HttpResponse(status=200)

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        logger.warning("Webhook MP: notificación de pago sin data.id.")
        return HttpResponse(status=200)

    # ── 2. Consultar detalle del pago a la API de MP ──────────────────────────
    try:
        mp_url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"}
        mp_response = requests.get(mp_url, headers=headers, timeout=10)
        mp_response.raise_for_status()
        payment = mp_response.json()

        logger.info(
            "Webhook MP: pago %s recibido con status '%s'.",
            payment_id, payment.get("status"),
        )

        # ── 3. Procesar solo pagos aprobados ──────────────────────────────────
        if payment.get("status") == "approved":
            payer_email = payment.get("payer", {}).get("email", "")
            transaction_amount = payment.get("transaction_amount", 0)
            external_reference = str(payment.get("id", payment_id))

            from ACCOUNTS.models import CustomUser
            from SUSCRIPCIONES.models import Pago, Plan, Suscripcion

            try:
                user = CustomUser.objects.get(email=payer_email)
            except CustomUser.DoesNotExist:
                logger.warning(
                    "Webhook MP: usuario no encontrado con email '%s'.", payer_email
                )
                return HttpResponse(status=200)

            # ── 3a. Actualizar campos de premium en CustomUser ────────────────
            now = timezone.now()
            nueva_fecha = (
                max(user.premium_until, now) if user.premium_until and user.premium_until > now
                else now
            ) + timedelta(days=30)

            user.is_premium    = True
            user.premium_until = nueva_fecha
            user.save(update_fields=["is_premium", "premium_until"])
            logger.info("Premium activado para usuario: %s hasta %s", user.username, nueva_fecha)

            # ── 3b. Obtener o crear Suscripcion activa ────────────────────────
            plan_premium, _ = Plan.objects.get_or_create(
                nombre=Plan.PREMIUM,
                defaults={"precio_mensual": transaction_amount},
            )
            suscripcion, created = Suscripcion.objects.update_or_create(
                usuario=user,
                defaults={
                    "plan": plan_premium,
                    "estado": Suscripcion.ACTIVA,
                    "fecha_vencimiento": nueva_fecha,
                },
            )
            if created:
                logger.info("Suscripcion creada para usuario: %s", user.username)

            # ── 3c. Registrar el Pago (evitar duplicados por referencia) ──────
            Pago.objects.update_or_create(
                referencia_gateway=external_reference,
                defaults={
                    "suscripcion": suscripcion,
                    "monto": transaction_amount,
                    "metodo": "mercadopago",
                    "exitoso": True,
                },
            )
            logger.info("Pago %s registrado para usuario: %s", external_reference, user.username)

    except requests.RequestException as exc:
        logger.error("Webhook MP: error consultando API de MP para pago %s: %s", payment_id, exc)
    except Exception as exc:
        logger.error("Webhook MP: error inesperado procesando pago %s: %s", payment_id, exc)

    # Siempre responder 200 para que MP no reintente
    return HttpResponse(status=200)


# ── Checkout Pro — flujo de prueba obligatorio para desbloquear el panel ──────

@login_required
def checkout_pro_prueba(request):
    """
    Genera una preferencia de Checkout Pro con un producto ficticio de $100 ARS
    y redirige al usuario al formulario de pago de MercadoPago.

    Este flujo es requerido por MP para validar la integración y desbloquear
    el menú de Suscripciones en el panel de desarrolladores.

    URL de prueba: http://localhost:8000/suscripciones/checkout-prueba/
    """
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    # Construir base URL pública desde MERCADOPAGO_BACK_URL para que MP acepte las back_urls.
    # request.build_absolute_uri devuelve localhost en dev, que MP rechaza con auto_return.
    _parsed = urlparse(settings.MERCADOPAGO_BACK_URL)
    _public_base = f"{_parsed.scheme}://{_parsed.netloc}"
    _is_public = _parsed.hostname not in ('localhost', '127.0.0.1', '0.0.0.0')

    preference_data = {
        "items": [
            {
                "title": "Monitorea Premium — prueba de integración",
                "quantity": 1,
                "unit_price": 100.00,
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": _public_base + reverse('suscripciones:pago_exitoso'),
            "failure": _public_base + reverse('suscripciones:pago_fallido'),
            "pending": _public_base + reverse('suscripciones:pago_pendiente'),
        },
        "payer": {
            "email": request.user.email,
        },
    }

    # auto_return solo funciona con URLs públicas (no localhost)
    if _is_public:
        preference_data["auto_return"] = "approved"

    response = sdk.preference().create(preference_data)

    if response["status"] == 201:
        init_point = response["response"]["init_point"]
        return redirect(init_point)

    error_detail = response.get("response", response)
    logger.error("Error creando preferencia Checkout Pro: %s", response)
    return HttpResponse(
        f"<pre style='font-family:monospace'>Error MP (HTTP {response.get('status')}):\n{error_detail}</pre>",
        status=500,
    )


def pago_exitoso(request):
    """MP redirige aquí cuando el pago fue aprobado — vuelve al dashboard."""
    return redirect('dashboard:dashboard')


def pago_fallido(request):
    """MP redirige aquí cuando el pago falló — vuelve a la página de planes."""
    return redirect('suscripciones:planes')


def pago_pendiente(request):
    """MP redirige aquí cuando el pago quedó pendiente — vuelve al dashboard."""
    return redirect('dashboard:dashboard')
