import hashlib
import hmac
import json
import logging
from datetime import timedelta
from urllib.parse import urlparse

import mercadopago
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
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


# ──────────────────────────────────────────────────────────────────────────────
# Suscripción recurrente (Preapproval) — débito automático mensual
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def crear_suscripcion(request):
    """
    Crea una suscripción recurrente (preapproval) en MercadoPago a partir de un
    plan previamente creado (MERCADOPAGO_PLAN_ID) y redirige al usuario al
    formulario de pago de MP.

    Requiere en settings:
      MERCADOPAGO_ACCESS_TOKEN  - token de acceso de la app MP
      MERCADOPAGO_PLAN_ID       - ID del plan de suscripción creado en MP

    El external_reference lleva el id del usuario para identificarlo en el webhook.
    """
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    _parsed = urlparse(settings.MERCADOPAGO_BACK_URL)
    _public_base = f"{_parsed.scheme}://{_parsed.netloc}"

    subscription_data = {
        "preapproval_plan_id": settings.MERCADOPAGO_PLAN_ID,
        "payer_email": request.user.email,
        "external_reference": str(request.user.id),
        "back_url": _public_base + reverse('suscripciones:pago_exitoso'),
    }

    response = sdk.preapproval().create(subscription_data)

    if response["status"] == 201:
        init_point = response["response"]["init_point"]
        return redirect(init_point)

    logger.error("Error creando suscripción MP: %s", response)
    return redirect('suscripciones:planes')


# ──────────────────────────────────────────────────────────────────────────────
# Validación de firma de MercadoPago (seguridad del webhook)
# ──────────────────────────────────────────────────────────────────────────────
def validar_firma_mp(request, data_id):
    """
    Valida el header x-signature que MercadoPago envía en cada notificación.
    Requiere settings.MERCADOPAGO_WEBHOOK_SECRET (clave secreta del panel MP).
    Si no hay secret configurado, se omite la validación (útil al empezar).
    """
    secret = getattr(settings, "MERCADOPAGO_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("Webhook MP: sin MERCADOPAGO_WEBHOOK_SECRET, se omite validación de firma.")
        return True

    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")

    try:
        partes = dict(p.strip().split("=", 1) for p in signature.split(",") if "=" in p)
    except ValueError:
        return False

    ts = partes.get("ts", "")
    v1 = partes.get("v1", "")
    if not ts or not v1:
        return False

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    hmac_calc = hmac.new(
        secret.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(hmac_calc, v1)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers para activar premium / registrar pago
# ──────────────────────────────────────────────────────────────────────────────
def _activar_premium(user, monto, referencia):
    """Activa premium, crea/actualiza Suscripcion y registra el Pago. Atómico."""
    from SUSCRIPCIONES.models import Pago, Plan, Suscripcion

    with transaction.atomic():
        now = timezone.now()
        base = user.premium_until if (user.premium_until and user.premium_until > now) else now
        nueva_fecha = base + timedelta(days=30)

        user.is_premium = True
        user.premium_until = nueva_fecha
        user.save(update_fields=["is_premium", "premium_until"])
        logger.info("Premium activado para %s hasta %s", user.username, nueva_fecha)

        plan_premium, _ = Plan.objects.get_or_create(
            nombre=Plan.PREMIUM,
            defaults={"precio_mensual": monto or 0},
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
            logger.info("Suscripcion creada para %s", user.username)

        Pago.objects.update_or_create(
            referencia_gateway=str(referencia),
            defaults={
                "suscripcion": suscripcion,
                "monto": monto or 0,
                "metodo": "mercadopago",
                "exitoso": True,
            },
        )
        logger.info("Pago %s registrado para %s", referencia, user.username)


def _buscar_usuario(external_reference, fallback_email=""):
    """Busca el usuario por external_reference (id) y, si falla, por email."""
    from ACCOUNTS.models import CustomUser

    if external_reference:
        try:
            return CustomUser.objects.get(id=external_reference)
        except (CustomUser.DoesNotExist, ValueError, TypeError):
            pass
    if fallback_email:
        try:
            return CustomUser.objects.get(email=fallback_email)
        except CustomUser.DoesNotExist:
            pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Webhook — recibe confirmación de PAGOS y de SUSCRIPCIONES recurrentes
# ──────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def webhook(request):
    """
    Recibe notificaciones de MercadoPago. Maneja dos tipos:
      - type='payment'      → pago único (Checkout Pro) o cuota de suscripción.
      - type='subscription_preapproval' → alta/cambio de estado de la suscripción.

    Siempre retorna HTTP 200 (salvo firma inválida → 401) para que MP no reintente.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Webhook MP: cuerpo JSON inválido.")
        return HttpResponse(status=200)

    notification_type = data.get("type") or data.get("action", "")
    resource_id = data.get("data", {}).get("id")

    if not resource_id:
        logger.warning("Webhook MP: notificación sin data.id.")
        return HttpResponse(status=200)

    # Validar firma
    if not validar_firma_mp(request, resource_id):
        logger.warning("Webhook MP: firma inválida (id=%s).", resource_id)
        return HttpResponse(status=401)

    headers = {"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"}

    try:
        # ── A. Notificación de PAGO ───────────────────────────────────────────
        if "payment" in notification_type:
            mp_url = f"https://api.mercadopago.com/v1/payments/{resource_id}"
            resp = requests.get(mp_url, headers=headers, timeout=10)
            resp.raise_for_status()
            payment = resp.json()

            logger.info("Webhook MP: pago %s status '%s'.", resource_id, payment.get("status"))

            if payment.get("status") == "approved":
                user = _buscar_usuario(
                    payment.get("external_reference"),
                    payment.get("payer", {}).get("email", ""),
                )
                if not user:
                    logger.warning("Webhook MP: usuario no encontrado (pago %s).", resource_id)
                    return HttpResponse(status=200)

                _activar_premium(
                    user,
                    payment.get("transaction_amount", 0),
                    payment.get("id", resource_id),
                )

        # ── B. Notificación de SUSCRIPCIÓN recurrente ─────────────────────────
        elif "preapproval" in notification_type or "subscription" in notification_type:
            mp_url = f"https://api.mercadopago.com/preapproval/{resource_id}"
            resp = requests.get(mp_url, headers=headers, timeout=10)
            resp.raise_for_status()
            preapproval = resp.json()

            estado = preapproval.get("status")
            logger.info("Webhook MP: suscripción %s status '%s'.", resource_id, estado)

            # status 'authorized' = suscripción activa
            if estado == "authorized":
                user = _buscar_usuario(
                    preapproval.get("external_reference"),
                    preapproval.get("payer_email", ""),
                )
                if not user:
                    logger.warning("Webhook MP: usuario no encontrado (sub %s).", resource_id)
                    return HttpResponse(status=200)

                monto = preapproval.get("auto_recurring", {}).get("transaction_amount", 0)
                _activar_premium(user, monto, resource_id)

    except requests.RequestException as exc:
        logger.error("Webhook MP: error consultando API MP (%s): %s", resource_id, exc)
    except Exception as exc:
        logger.error("Webhook MP: error inesperado (%s): %s", resource_id, exc)

    return HttpResponse(status=200)


# ──────────────────────────────────────────────────────────────────────────────
# Checkout Pro — pago único (flujo de prueba de integración)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def checkout_pro_prueba(request):
    """
    Genera una preferencia de Checkout Pro (pago único) y redirige a MP.
    Útil para validar la integración. external_reference = id del usuario.
    """
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    _parsed = urlparse(settings.MERCADOPAGO_BACK_URL)
    _public_base = f"{_parsed.scheme}://{_parsed.netloc}"
    _is_public = _parsed.hostname not in ('localhost', '127.0.0.1', '0.0.0.0')

    preference_data = {
        "items": [
            {
                "title": "Monitorea Premium — prueba de integración",
                "quantity": 1,
                "unit_price": 200.00,
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
        "external_reference": str(request.user.id),
        "notification_url": _public_base + reverse('suscripciones:webhook'),
    }

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