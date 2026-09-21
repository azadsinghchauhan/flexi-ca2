import os
import sys

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app


class VercelPathMiddleware(object):
    """
    WSGI Middleware to fix Vercel serverless path routing.
    When Vercel rewrites requests to /api/index, PATH_INFO can contain '/api/index'
    or '/api/index.py'. This middleware restores the true client request path.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Prefer HTTP_X_FORWARDED_URI or HTTP_X_MATCHED_PATH header sent by Vercel Edge
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
        if forwarded_uri:
            clean_path = forwarded_uri.split("?")[0]
            environ["PATH_INFO"] = clean_path if clean_path else "/"
        else:
            # 2. Fallback: Strip /api/index.py or /api/index prefix from PATH_INFO
            path = environ.get("PATH_INFO", "")
            if path.startswith("/api/index.py"):
                environ["PATH_INFO"] = path[len("/api/index.py"):] or "/"
            elif path.startswith("/api/index"):
                environ["PATH_INFO"] = path[len("/api/index"):] or "/"

        return self.wsgi_app(environ, start_response)


# Wrap Flask's WSGI application with the Vercel path resolver
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
