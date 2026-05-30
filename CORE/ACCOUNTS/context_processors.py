def user_theme(request):
    """Inyecta la preferencia de tema del usuario en todos los templates."""
    theme = 'auto'
    if request.user.is_authenticated:
        theme = getattr(request.user, 'theme', 'auto')
    return {'user_theme': theme}
