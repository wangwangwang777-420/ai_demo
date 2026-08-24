"""WSGI 入口：生产环境由 uWSGI / gunicorn / 云厂商托管"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_demo.settings")

application = get_wsgi_application()
