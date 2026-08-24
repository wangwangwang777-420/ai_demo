from django.apps import AppConfig


class ChatConfig(AppConfig):
    """chat 应用配置：Django 会依据这里注册的 app 名称加载 models 等模块"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"
