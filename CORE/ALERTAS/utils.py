import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def enviar_alerta_whatsapp(to_number: str, mensaje: str) -> bool:
    """
    Envía un mensaje de WhatsApp vía Twilio.

    Parámetros:
        to_number — Número destino (ej: +5491122334455 o whatsapp:+5491122334455)
        mensaje   — Texto del mensaje a enviar

    Retorna True si el envío fue exitoso, False en caso contrario.
    """
    account_sid   = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token    = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number   = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')

    if not all([account_sid, auth_token, from_number]):
        logger.warning('[ALERTAS] Credenciales Twilio no configuradas. Alerta no enviada.')
        return False

    # Asegurarse de que el número destino tenga el prefijo whatsapp:
    if not to_number.startswith('whatsapp:'):
        to_number = f'whatsapp:{to_number}'

    try:
        from twilio.rest import Client  # import diferido — no rompe si twilio no está instalado
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=mensaje,
            from_=from_number,
            to=to_number,
        )
        logger.info('[ALERTAS] WhatsApp enviado. SID: %s', message.sid)
        return True
    except Exception as exc:
        logger.error('[ALERTAS] Error al enviar WhatsApp a %s: %s', to_number, exc)
        return False
