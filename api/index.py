import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(parent_dir, "backend")

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app as fastapi_app

class VercelPathFixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            headers = dict(scope.get("headers", []))
            
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8")
            forwarded_uri = headers.get(b"x-forwarded-uri", b"").decode("utf-8")
            
            if matched_path and matched_path != "/api/index.py" and not matched_path.startswith("/api/"):
                scope["path"] = matched_path.split("?")[0]
            elif forwarded_uri and not forwarded_uri.startswith("/api/"):
                scope["path"] = forwarded_uri.split("?")[0]
            elif path.startswith("/api/index.py"):
                new_path = path[len("/api/index.py"):]
                if new_path:
                    scope["path"] = new_path
            elif path.startswith("/api"):
                new_path = path[len("/api"):]
                if new_path:
                    scope["path"] = new_path

        await self.app(scope, receive, send)

app = VercelPathFixMiddleware(fastapi_app)
