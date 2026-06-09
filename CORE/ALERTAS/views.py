import logging
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from DASHBOARD.models import Dispositivo
from SUSCRIPCIONES.decorators import requiere_premium

from .models import ConfiguracionAlerta, HistorialAlerta

logger = logging.getLogger(__name__)


# ── E: Twilio helper ───────────────────────────────────────────────────────────────

def enviar_alerta_whatsapp(to_number: str, mensaje: str) -> bool:
    """
    Envia un mensaje de WhatsApp via Twilio.
    Lee TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_WHATSAPP_FROM de settings.
    """
    try:
        from twilio.rest import Client
    except ImportError:
        logger.error('[ALERTAS] Twilio no esta instalado.')
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')

    if not all([account_sid, auth_token, from_number]):
        logger.warning('[ALERTAS] Credenciales Twilio no configuradas.')
        return False

    if not to_number.startswith('whatsapp:'):
        to_number = f'whatsapp:{to_number}'
    if not from_number.startswith('whatsapp:'):
        from_number = f'whatsapp:{from_number}'

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(body=mensaje, from_=from_number, to=to_number)
        logger.info('[ALERTAS] WhatsApp enviado a %s', to_number)
        return True
    except Exception as exc:
        logger.error('[ALERTAS] Error Twilio: %s', exc)
        return False


# ── F: Signal handler para post_save de Telemetria ───────────────────────────────────

def handle_nueva_telemetria(sender, instance, created, **kwargs):
    """
    Se ejecuta en cada post_save de Telemetria (solo nuevos registros).
    Evalua umbrales, respeta cooldown y envia alerta WhatsApp si corresponde.
    Conectado en AlertasConfig.ready().
    """
    if not created:
        return

    try:
        config = ConfiguracionAlerta.objects.get(
            dispositivo=instance.dispositivo,
            tipo_sensor=instance.tipo_sensor,
            activo=True,
        )
    except ConfiguracionAlerta.DoesNotExist:
        return

    usuario = instance.dispositivo.establecimiento.usuario
    try:
        if not usuario.tiene_premium_activo():
            return
    except Exception:
        return

    valor = instance.valor
    fuera_de_rango = (
        (config.min_valor is not None and valor < config.min_valor) or
        (config.max_valor is not None and valor > config.max_valor)
    )
    if not fuera_de_rango:
        return

    ahora    = timezone.now()
    cooldown = getattr(settings, 'ALERT_COOLDOWN_SEGUNDOS', 300)
    if config.ultima_notificacion is not None:
        if (ahora - config.ultima_notificacion).total_seconds() < cooldown:
            logger.debug('[ALERTAS] Cooldown activo: %s / %s', instance.dispositivo, instance.tipo_sensor)
            return

    unidad  = '\u00b0C' if instance.tipo_sensor == 'temperatura' else ''
    mensaje = (
        f'\u00a1Alerta de Emergencia! El sensor {instance.tipo_sensor.capitalize()} '
        f'del dispositivo {instance.dispositivo.nombre} ha registrado {valor}{unidad}, '
        f'fuera del rango seguro ({config.min_valor} - {config.max_valor}).'
    )

    if config.whatsapp_destino:
        enviar_alerta_whatsapp(config.whatsapp_destino, mensaje)

    config.ultima_notificacion = ahora
    config.save(update_fields=['ultima_notificacion'])

    HistorialAlerta.objects.create(
        dispositivo=instance.dispositivo,
        tipo_sensor=instance.tipo_sensor,
        valor_disparador=valor,
        mensaje=mensaje,
    )


# ── B: Vistas ─────────────────────────────────────────────────────────────────────

@login_required
@requiere_premium
def alertas_index(request):
    """Vista principal: dispositivos agrupados por establecimiento con sus configs de alerta."""
    dispositivos = list(
        Dispositivo.objects
        .filter(establecimiento__usuario=request.user)
        .prefetch_related('alertas')
        .select_related('establecimiento')
        .order_by('establecimiento__nombre', 'nombre')
    )

    establecimientos = defaultdict(list)
    for disp in dispositivos:
        try:
            cfg_temp = disp.alertas.get(tipo_sensor='temperatura')
        except ConfiguracionAlerta.DoesNotExist:
            cfg_temp = None
        establecimientos[disp.establecimiento].append((disp, cfg_temp))

    return render(request, 'ALERTAS/alertas.html', {'establecimientos': dict(establecimientos)})


@login_required
@requiere_premium
@require_POST
def guardar_alerta(request):
    """Crea o actualiza la configuracion de alerta para un dispositivo/sensor."""
    dispositivo_id   = request.POST.get('dispositivo_id', '').strip()
    tipo_sensor      = request.POST.get('tipo_sensor', '').strip()
    min_valor_raw    = request.POST.get('min_valor', '').strip()
    max_valor_raw    = request.POST.get('max_valor', '').strip()
    whatsapp_destino = request.POST.get('whatsapp_destino', '').strip()

    dispositivo = get_object_or_404(
        Dispositivo,
        id=dispositivo_id,
        establecimiento__usuario=request.user,
    )

    try:
        min_valor = float(min_valor_raw) if min_valor_raw else None
        max_valor = float(max_valor_raw) if max_valor_raw else None
    except ValueError:
        messages.error(request, 'Los valores de umbral deben ser numeros.')
        return redirect('alertas:alertas_index')

    ConfiguracionAlerta.objects.update_or_create(
        dispositivo=dispositivo,
        tipo_sensor=tipo_sensor,
        defaults={
            'min_valor':        min_valor,
            'max_valor':        max_valor,
            'whatsapp_destino': whatsapp_destino or None,
        },
    )

    messages.success(
        request,
        f'Configuracion guardada para {dispositivo.nombre} ({tipo_sensor}).',
    )
    return redirect('alertas:alertas_index')
