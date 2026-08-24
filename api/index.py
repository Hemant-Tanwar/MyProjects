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
            if path.startswith("/api/index.py"):
                new_path = path[len("/api/index.py"):]
                scope["path"] = new_path if new_path else "/"
            elif path.startswith("/api"):
                new_path = path[len("/api"):]
                scope["path"] = new_path if new_path else "/"
        await self.app(scope, receive, send)

app = VercelPathFixMiddleware(fastapi_app)
