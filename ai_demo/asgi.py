"""ASGI 入口：预留，后续如需 WebSocket / 生产部署可在此扩展"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_demo.settings")

application = get_asgi_application()
