from django.conf import settings

def session_timeout_settings(request):
    """
    Makes session timeout values available in all templates.
    """
    return {
        'SESSION_IDLE_TIMEOUT': getattr(settings, 'SESSION_IDLE_TIMEOUT', 60),
        'SESSION_WARNING_TIME': getattr(settings, 'SESSION_WARNING_TIME', 30),
    }
