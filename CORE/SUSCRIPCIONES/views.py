import hashlib
import hmac
import json
import logging
import random
import string
from datetime import timedelta
from urllib.parse import urlparse

import mercadopago
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@login_required
def planes(request):
    """Página de planes — muestra opciones o el plan activo del usuario."""
    from SUSCRIPCIONES.models import Plan

    suscripcion = None
    dias_restantes = None
    color_tarjeta = 'success'

    try:
        suscripcion = request.user.suscripcion
    except Exception:
        pass

    if suscripcion and suscripcion.esta_activa():
        delta = suscripcion.fecha_vencimiento - timezone.now()
        dias_restantes = max(delta.days, 0)
        es_anual = suscripcion.plan.nombre == Plan.ANUAL
        umbral = 30 if es_anual else 10
        if dias_restantes < umbral:
            color_tarjeta = 'warning'

    # Precio base mensual y anual para mostrar en las tarjetas
    precio_mensual = getattr(settings, 'PRECIO_MENSUAL', 4999)
    precio_anual = precio_mensual * 10

    context = {
        'suscripcion': suscripcion,
        'dias_restantes': dias_restantes,
        'color_tarjeta': color_tarjeta,
        'precio_mensual': precio_mensual,
        'precio_anual': precio_anual,
    }
    return render(request, 'SUSCRIPCIONES/planes.html', context)


# ──────────────────────────────────────────────────────────────────────────────
# Cancelación de suscripción — flujo por email con código de 6 dígitos
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def solicitar_codigo_cancelacion(request):
    """
    Genera un código aleatorio de 6 dígitos, lo guarda en la suscripción y
    lo envía por correo. Responde JSON.
    """
    from SUSCRIPCIONES.models import Suscripcion

    try:
        suscripcion = request.user.suscripcion
    except Suscripcion.DoesNotExist:
        return JsonResponse({'error': 'No tenés una suscripción activa.'}, status=400)

    if not suscripcion.esta_activa():
        return JsonResponse({'error': 'No tenés una suscripción activa.'}, status=400)

    codigo = ''.join(random.choices(string.digits, k=6))
    suscripcion.codigo_cancelacion = codigo
    suscripcion.save(update_fields=['codigo_cancelacion'])

    try:
        send_mail(
            subject='Código de cancelación — Monitorea',
            message=(
                f'Hola {request.user.username},\n\n'
                f'Tu código de confirmación para anular la suscripción es:\n\n'
                f'    {codigo}\n\n'
                'Si no solicitaste este código, ignorá este mensaje.\n\n'
                'Equipo Monitorea'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Error enviando email de cancelación a %s: %s", request.user.email, exc)
        return JsonResponse({'error': 'No se pudo enviar el correo. Intentá nuevamente.'}, status=500)

    return JsonResponse({'ok': True})


@login_required
@require_POST
def confirmar_cancelacion(request):
    """
    Verifica el código ingresado, cancela la suscripción en Mercado Pago y
    actualiza el estado local del usuario. Responde JSON.
    """
    from SUSCRIPCIONES.models import Suscripcion

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    codigo_ingresado = str(data.get('codigo', '')).strip()

    try:
        suscripcion = request.user.suscripcion
    except Suscripcion.DoesNotExist:
        return JsonResponse({'error': 'No tenés una suscripción activa.'}, status=400)

    if not suscripcion.esta_activa():
        return JsonResponse({'error': 'No tenés una suscripción activa.'}, status=400)

    if not suscripcion.codigo_cancelacion or suscripcion.codigo_cancelacion != codigo_ingresado:
        return JsonResponse({'error': 'Código incorrecto. Revisá tu correo e intentá nuevamente.'}, status=400)

    # Cancelar en Mercado Pago si hay una suscripción recurrente vinculada
    if suscripcion.gateway_subscription_id:
        try:
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            response = sdk.preapproval().update(
                suscripcion.gateway_subscription_id,
                {"status": "cancelled"},
            )
            if response.get("status") not in (200, 201):
                logger.error("Error cancelando suscripción MP (id=%s): %s",
                             suscripcion.gateway_subscription_id, response)
                return JsonResponse(
                    {'error': 'No se pudo cancelar en Mercado Pago. Intentá más tarde.'},
                    status=502,
                )
        except Exception as exc:
            logger.error("Excepción al cancelar suscripción MP: %s", exc)
            return JsonResponse({'error': 'Error al comunicarse con Mercado Pago.'}, status=502)

    # Actualizar estado local de forma atómica
    with transaction.atomic():
        suscripcion.estado = Suscripcion.CANCELADA
        suscripcion.codigo_cancelacion = None
        suscripcion.save(update_fields=['estado', 'codigo_cancelacion'])

        user = request.user
        user.is_premium = False
        user.premium_until = None
        user.save(update_fields=['is_premium', 'premium_until'])

    logger.info("Suscripción cancelada para el usuario %s.", user.username)
    return JsonResponse({'ok': True})


# ──────────────────────────────────────────────────────────────────────────────
# Suscripción recurrente (Preapproval) — débito automático mensual
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def crear_suscripcion(request, tipo):
    """
    Redirige al usuario al checkout de suscripción recurrente de MercadoPago
    usando directamente el init_point del plan.
    `tipo` puede ser 'mensual' o 'anual'.

    Requiere en settings:
      MERCADOPAGO_PLAN_ID_MENSUAL  - ID del plan mensual creado en MP
      MERCADOPAGO_PLAN_ID_ANUAL    - ID del plan anual creado en MP
    """
    PLANES_ID = {
        'mensual': getattr(settings, 'MERCADOPAGO_PLAN_ID_MENSUAL', ''),
        'anual':   getattr(settings, 'MERCADOPAGO_PLAN_ID_ANUAL',   ''),
    }

    if tipo not in PLANES_ID:
        logger.error("crear_suscripcion: tipo '%s' inválido.", tipo)
        return redirect('suscripciones:planes')

    plan_id = PLANES_ID[tipo]
    if not plan_id:
        logger.error("crear_suscripcion: MERCADOPAGO_PLAN_ID_%s no está configurado.", tipo.upper())
        return redirect('suscripciones:planes')

    init_point = f"https://www.mercadopago.com.ar/subscriptions/checkout?preapproval_plan_id={plan_id}"
    return redirect(init_point)


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
def _activar_premium(user, monto, referencia, gateway_subscription_id=None, dias=30, tipo_plan=None):
    """Activa premium, crea/actualiza Suscripcion y registra el Pago. Atómico."""
    from SUSCRIPCIONES.models import Pago, Plan, Suscripcion

    with transaction.atomic():
        now = timezone.now()
        base = user.premium_until if (user.premium_until and user.premium_until > now) else now
        nueva_fecha = base + timedelta(days=dias)

        user.is_premium = True
        user.premium_until = nueva_fecha
        user.save(update_fields=["is_premium", "premium_until"])
        logger.info("Premium activado para %s hasta %s (%s días)", user.username, nueva_fecha, dias)

        # Elegir el tipo de plan según lo indicado; por defecto Plan.PREMIUM (legado)
        _nombre_plan = {
            'mensual': Plan.MENSUAL,
            'anual':   Plan.ANUAL,
        }.get(tipo_plan, Plan.PREMIUM)

        plan_obj, _ = Plan.objects.get_or_create(
            nombre=_nombre_plan,
            defaults={"precio_mensual": monto or 0},
        )

        sub_defaults = {
            "plan": plan_obj,
            "estado": Suscripcion.ACTIVA,
            "fecha_vencimiento": nueva_fecha,
        }
        if gateway_subscription_id:
            sub_defaults["gateway_subscription_id"] = gateway_subscription_id

        suscripcion, created = Suscripcion.objects.update_or_create(
            usuario=user,
            defaults=sub_defaults,
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
                external_ref = preapproval.get("external_reference", "")
                # external_reference puede ser "<user_id>:mensual" o "<user_id>:anual"
                ref_parts = str(external_ref).split(":")
                user_id = ref_parts[0]
                tipo = ref_parts[1] if len(ref_parts) > 1 else 'mensual'

                user = _buscar_usuario(user_id, preapproval.get("payer_email", ""))
                if not user:
                    logger.warning("Webhook MP: usuario no encontrado (sub %s).", resource_id)
                    return HttpResponse(status=200)

                monto = preapproval.get("auto_recurring", {}).get("transaction_amount", 0)
                dias  = 365 if tipo == 'anual' else 30
                _activar_premium(
                    user, monto, resource_id,
                    gateway_subscription_id=resource_id,
                    dias=dias,
                    tipo_plan=tipo,
                )

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