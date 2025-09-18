import datetime
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

class SessionTimeoutMiddleware:
    """
    Middleware to log out users after `SESSION_IDLE_TIMEOUT` seconds of inactivity.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = datetime.datetime.utcnow().timestamp()
            last_activity = request.session.get('last_activity')

            if last_activity:
                elapsed = current_time - last_activity
                if elapsed > getattr(settings, 'SESSION_IDLE_TIMEOUT', 900):
                    from django.contrib.auth import logout
                    logout(request)
                    messages.info(request, "Your session has expired due to inactivity.")
                    return redirect('login')  # Adjust to your login URL name

            # Update last activity timestamp
            request.session['last_activity'] = current_time

        return self.get_response(request)
