"""chat 应用路由"""
from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # 首页：IM 风格聊天页面
    path("", views.index, name="index"),
    # 流式对话接口
    path("api/chat", views.chat_api, name="chat_api"),
]
