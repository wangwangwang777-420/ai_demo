#!/usr/bin/env python
"""Django 命令行工具入口"""
import os
import sys


def main():
    """运行管理命令（runserver / migrate / makemigrations 等）"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_demo.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
