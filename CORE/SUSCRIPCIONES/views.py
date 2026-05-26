import json
import logging

import mercadopago
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import timedelta

logger = logging.getLogger(__name__)


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
    Recibe notificaciones IPN de MercadoPago sobre el estado de las
    suscripciones (preapproval).

    Cuando el estado es 'authorized' (pago aprobado):
      - Busca el usuario por email
      - Activa is_premium = True
      - Establece premium_until = now + 30 días

    IMPORTANTE: esta URL debe ser pública.
    Para desarrollo local usá ngrok: ngrok http 8000
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # MP envía notificaciones de tipo 'preapproval' para suscripciones recurrentes
    if data.get("type") != "preapproval":
        return HttpResponse(status=200)

    preapproval_id = data.get("data", {}).get("id")
    if not preapproval_id:
        return HttpResponse(status=200)

    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        response = sdk.preapproval().get(preapproval_id)
        preapproval = response.get("response", {})

        if preapproval.get("status") == "authorized":
            payer_email = preapproval.get("payer_email", "")

            from ACCOUNTS.models import CustomUser
            try:
                user = CustomUser.objects.get(email=payer_email)
                user.is_premium    = True
                user.premium_until = timezone.now() + timedelta(days=30)
                user.save(update_fields=['is_premium', 'premium_until'])
                logger.info("Premium activado para usuario: %s", user.username)
            except CustomUser.DoesNotExist:
                logger.warning("Webhook MP: usuario no encontrado con email %s", payer_email)

    except Exception as exc:
        logger.error("Error procesando webhook MP: %s", exc)

    # Siempre responder 200 para que MP no reintente
    return HttpResponse(status=200)
