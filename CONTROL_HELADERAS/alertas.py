"""
alertas.py
==========
Módulo de alertas por WhatsApp usando Twilio.

Envía mensajes de WhatsApp cuando temperatura o voltaje superan
los umbrales configurados. Incluye cooldown por sensor para evitar
inundación de mensajes.

──────────────────────────────────────────────────────────────
CONFIGURACIÓN (variables de entorno requeridas):
──────────────────────────────────────────────────────────────
  TWILIO_ACCOUNT_SID   → SID de tu cuenta Twilio
  TWILIO_AUTH_TOKEN    → Auth token de Twilio
  TWILIO_WHATSAPP_FROM → Número Twilio (ej: whatsapp:+14155238886)
  TWILIO_WHATSAPP_TO   → Tu número destino (ej: whatsapp:+5491112345678)

Umbrales configurables:
  TEMP_MAX   → Temperatura máxima permitida (default: 8.0 °C)
  TEMP_MIN   → Temperatura mínima permitida (default: -25.0 °C)
  VOLT_MAX   → Voltaje máximo permitido     (default: 240.0 V)
  VOLT_MIN   → Voltaje mínimo permitido     (default: 190.0 V)
  ALERT_COOLDOWN_SEGUNDOS → Segundos entre alertas del mismo sensor (default: 300)
──────────────────────────────────────────────────────────────
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Carga el .env desde la raíz del proyecto (un nivel arriba de este archivo)
_ENV_FILE = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=_ENV_FILE)

logger = logging.getLogger(__name__)

# ── UMBRALES ─────────────────────────────────────────────────────────────────
TEMP_MAX = float(os.environ.get('TEMP_MAX', '8.0'))
TEMP_MIN = float(os.environ.get('TEMP_MIN', '-25.0'))
VOLT_MAX = float(os.environ.get('VOLT_MAX', '240.0'))
VOLT_MIN = float(os.environ.get('VOLT_MIN', '190.0'))

# Segundos mínimos entre dos alertas del mismo sensor (cooldown anti-flood)
ALERT_COOLDOWN = int(os.environ.get('ALERT_COOLDOWN_SEGUNDOS', '300'))

# ── TWILIO CONFIG ─────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN    = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')  # ej: whatsapp:+14155238886
TWILIO_WHATSAPP_TO   = os.environ.get('TWILIO_WHATSAPP_TO', '')    # ej: whatsapp:+5491112345678
# ─────────────────────────────────────────────────────────────────────────────

# Registro de última alerta por sensor: { sensor_id: timestamp }
_ultimo_envio: dict[str, float] = {}


def _twilio_disponible() -> bool:
    """Verifica que las credenciales Twilio estén configuradas."""
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
                and TWILIO_WHATSAPP_FROM and TWILIO_WHATSAPP_TO)


def _en_cooldown(sensor_id: str) -> bool:
    """Devuelve True si el sensor todavía está en período de cooldown."""
    ultimo = _ultimo_envio.get(sensor_id, 0)
    return (time.time() - ultimo) < ALERT_COOLDOWN


def _enviar_whatsapp(mensaje: str) -> bool:
    """
    Envía un mensaje de WhatsApp vía Twilio.
    Retorna True si el envío fue exitoso, False en caso contrario.
    """
    try:
        from twilio.rest import Client  # import diferido para no romper si twilio no está instalado
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=mensaje,
            from_=TWILIO_WHATSAPP_FROM,
            to=TWILIO_WHATSAPP_TO,
        )
        logger.info('[ALERTA] WhatsApp enviado. SID: %s', message.sid)
        return True
    except Exception as exc:
        logger.error('[ALERTA] Error al enviar WhatsApp: %s', exc)
        return False


def verificar_temperatura(sensor_id: str, valor: float) -> Optional[str]:
    """
    Evalúa si la temperatura está fuera de rango y, si corresponde, envía alerta.

    Returns:
        Razón de la alerta si se envió, None si todo está bien o está en cooldown.
    """
    if TEMP_MIN <= valor <= TEMP_MAX:
        return None

    if _en_cooldown(sensor_id):
        logger.debug('[ALERTA] Temperatura fuera de rango pero en cooldown: %s', sensor_id)
        return None

    if valor > TEMP_MAX:
        razon = f'🌡️ *ALERTA DE TEMPERATURA ALTA*\nSensor: {sensor_id}\nValor: {valor:.1f}°C\nMáximo permitido: {TEMP_MAX}°C'
    else:
        razon = f'🌡️ *ALERTA DE TEMPERATURA BAJA*\nSensor: {sensor_id}\nValor: {valor:.1f}°C\nMínimo permitido: {TEMP_MIN}°C'

    mensaje = (
        f'⚠️ Heladería Perlatto — Alerta Automática\n\n'
        f'{razon}\n\n'
        f'Por favor revisá el equipo.'
    )

    if not _twilio_disponible():
        logger.warning('[ALERTA] Credenciales Twilio no configuradas. Alerta no enviada: %s', razon)
        return None

    if _enviar_whatsapp(mensaje):
        _ultimo_envio[sensor_id] = time.time()
        return razon

    return None


def verificar_voltaje(sensor_id: str, valor: float) -> Optional[str]:
    """
    Evalúa si el voltaje está fuera de rango y, si corresponde, envía alerta.

    Returns:
        Razón de la alerta si se envió, None si todo está bien o está en cooldown.
    """
    if VOLT_MIN <= valor <= VOLT_MAX:
        return None

    if _en_cooldown(sensor_id):
        logger.debug('[ALERTA] Voltaje fuera de rango pero en cooldown: %s', sensor_id)
        return None

    if valor > VOLT_MAX:
        razon = f'⚡ *ALERTA DE VOLTAJE ALTO*\nSensor: {sensor_id}\nValor: {valor:.1f}V\nMáximo permitido: {VOLT_MAX}V'
    else:
        razon = f'⚡ *ALERTA DE VOLTAJE BAJO*\nSensor: {sensor_id}\nValor: {valor:.1f}V\nMínimo permitido: {VOLT_MIN}V'

    mensaje = (
        f'⚠️ Heladería Perlatto — Alerta Automática\n\n'
        f'{razon}\n\n'
        f'Por favor revisá el equipo.'
    )

    if not _twilio_disponible():
        logger.warning('[ALERTA] Credenciales Twilio no configuradas. Alerta no enviada: %s', razon)
        return None

    if _enviar_whatsapp(mensaje):
        _ultimo_envio[sensor_id] = time.time()
        return razon

    return None
