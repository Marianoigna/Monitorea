@login_required
def crear_suscripcion(request, tipo):
    if tipo not in ('mensual', 'anual'):
        return redirect('suscripciones:planes')

    precio_mensual = getattr(settings, 'PRECIO_MENSUAL', 39900)
    monto = precio_mensual if tipo == 'mensual' else precio_mensual * 10
    frecuencia = 1 if tipo == 'mensual' else 12  # meses

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    _parsed = urlparse(settings.MERCADOPAGO_BACK_URL)
    _public_base = f"{_parsed.scheme}://{_parsed.netloc}"
    back_url = _public_base + reverse('suscripciones:pago_exitoso')
    notification_url = _public_base + reverse('suscripciones:webhook')

    preapproval_data = {
        "reason": f"Monitorea Premium — {tipo}",
        "auto_recurring": {
            "frequency": frecuencia,
            "frequency_type": "months",
            "transaction_amount": float(monto),
            "currency_id": "ARS",
        },
        "back_url": back_url,
        "payer_email": request.user.email,
        "external_reference": f"{request.user.id}:{tipo}",   # ← viaja el usuario
        "notification_url": notification_url,                 # ← viaja el webhook
        "status": "pending",
    }

    response = sdk.preapproval().create(preapproval_data)

    if response["status"] in (200, 201):
        init_point = response["response"]["init_point"]
        return redirect(init_point)

    logger.error("Error creando suscripción MP: %s", response)
    return redirect('suscripciones:planes')
