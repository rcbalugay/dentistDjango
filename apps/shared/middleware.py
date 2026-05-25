import threading

_thread_locals = threading.local()

def get_current_request():
    return getattr(_thread_locals, "request", None)

def get_current_user():
    request = get_current_request()
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    return None

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            if hasattr(_thread_locals, "request"):
                del _thread_locals.request
        return response
