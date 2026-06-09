import csv
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from DASHBOARD.models import Dispositivo, Establecimiento, Telemetria
from SUSCRIPCIONES.decorators import requiere_premium

TIPO_LABELS = {
    'temperatura': 'Temperatura (°C)',
    'tension':     'Tensión (V)',
    'corriente':   'Corriente (A)',
    'humedad':     'Humedad (%)',
    'presion':     'Presión (hPa)',
}


@requiere_premium
def index(request):
    """
    Vista principal de reportes.
    Pasa al template los establecimientos con sus dispositivos
    para construir el formulario de filtros. Los datos se cargan vía AJAX.
    """
    establecimientos = (
        Establecimiento.objects
        .filter(usuario=request.user)
        .prefetch_related('dispositivos')
        .order_by('nombre')
    )

    context = {
        'establecimientos': establecimientos,
    }
    return render(request, 'REPORTES/reportes.html', context)


@requiere_premium
def obtener_datos_reporte(request):
    """
    Endpoint AJAX — devuelve telemetría filtrada en JSON.

    Parámetros GET:
      mac_address  — MAC del dispositivo (obligatorio)
      tipo_sensor  — temperatura | tension | corriente | humedad | presion (obligatorio)
      canal        — índice de canal, default 0
      fecha_inicio — YYYY-MM-DD, default hace 7 días
      fecha_fin    — YYYY-MM-DD, default hoy
    """
    # Para llamadas AJAX desde el template, si no hay premium el decorator
    # ya redirigió; pero si se llama directo devolvemos JSON limpio.
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    if not request.user.tiene_premium_activo():
        return JsonResponse({'error': 'Se requiere suscripción premium'}, status=403)

    mac_address  = request.GET.get('mac_address', '').strip()
    tipo_sensor  = request.GET.get('tipo_sensor', '').strip()
    canal_raw    = request.GET.get('canal', '0').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin    = request.GET.get('fecha_fin', '').strip()

    if not mac_address or not tipo_sensor:
        return JsonResponse(
            {'error': 'Los parámetros mac_address y tipo_sensor son obligatorios'},
            status=400,
        )

    try:
        canal = int(canal_raw)
    except ValueError:
        return JsonResponse({'error': 'canal debe ser un número entero'}, status=400)

    # Fechas por defecto
    hoy = timezone.now()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = hoy.strftime('%Y-%m-%d')

    # Verificar que el dispositivo pertenece al usuario (aislamiento multi-usuario)
    try:
        dispositivo = Dispositivo.objects.get(
            mac_address=mac_address,
            establecimiento__usuario=request.user,
        )
    except Dispositivo.DoesNotExist:
        return JsonResponse({'error': 'Dispositivo no encontrado'}, status=404)

    lecturas_qs = (
        Telemetria.objects
        .filter(
            dispositivo=dispositivo,
            tipo_sensor=tipo_sensor,
            canal=canal,
            timestamp__date__gte=fecha_inicio,
            timestamp__date__lte=fecha_fin,
        )
        .order_by('timestamp')
        .values('timestamp', 'valor')
    )

    lecturas = [
        {
            'timestamp': timezone.localtime(l['timestamp']).strftime('%Y-%m-%dT%H:%M:%S'),
            'valor':     l['valor'],
        }
        for l in lecturas_qs
    ]

    return JsonResponse({
        'ok':           True,
        'dispositivo':  dispositivo.nombre,
        'mac':          mac_address,
        'tipo_sensor':  tipo_sensor,
        'canal':        canal,
        'unidad':       TIPO_LABELS.get(tipo_sensor, tipo_sensor),
        'fecha_inicio': fecha_inicio,
        'fecha_fin':    fecha_fin,
        'total':        len(lecturas),
        'lecturas':     lecturas,
    })


@requiere_premium
def exportar_csv(request):
    """Exporta las lecturas filtradas como archivo CSV."""
    mac_sel     = request.GET.get('mac_address', request.GET.get('mac', '')).strip()
    tipo_sel    = request.GET.get('tipo_sensor', request.GET.get('tipo', '')).strip()
    canal_raw   = request.GET.get('canal', '0').strip()
    fecha_desde = request.GET.get('fecha_inicio', request.GET.get('fecha_desde', '')).strip()
    fecha_hasta = request.GET.get('fecha_fin', request.GET.get('fecha_hasta', '')).strip()

    try:
        canal = int(canal_raw)
    except ValueError:
        canal = 0

    hoy = timezone.now()
    if not fecha_desde:
        fecha_desde = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
    if not fecha_hasta:
        fecha_hasta = hoy.strftime('%Y-%m-%d')

    lecturas = (
        Telemetria.objects
        .filter(
            dispositivo__establecimiento__usuario=request.user,
            timestamp__date__gte=fecha_desde,
            timestamp__date__lte=fecha_hasta,
        )
        .select_related('dispositivo')
        .order_by('-timestamp')
    )

    if mac_sel:
        lecturas = lecturas.filter(dispositivo__mac_address=mac_sel)
    if tipo_sel:
        lecturas = lecturas.filter(tipo_sensor=tipo_sel, canal=canal)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    nombre_archivo = f'reporte_{fecha_desde}_{fecha_hasta}.csv'
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    response.write('\ufeff')  # BOM para compatibilidad con Excel
    writer = csv.writer(response)
    writer.writerow(['Dispositivo', 'MAC', 'Tipo sensor', 'Canal', 'Valor', 'Timestamp'])

    for l in lecturas:
        writer.writerow([
            l.dispositivo.nombre,
            l.dispositivo.mac_address,
            l.tipo_sensor,
            l.canal,
            l.valor,
            timezone.localtime(l.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response
