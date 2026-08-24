"""根 URLconf：把 chat 应用挂载到根路径，同时挂载 Django Admin"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # chat 应用自带的 URLconf（首页 + /api/chat 接口）
    path("", include("chat.urls")),
]
