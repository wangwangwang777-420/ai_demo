"""Django Admin 后台：方便查看/排查对话记录"""
from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """对话消息的后台管理配置"""

    list_display = ("session_id", "role", "content_preview", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("session_id", "content")
    date_hierarchy = "created_at"
    # 只读，避免在后台误改生产数据
    readonly_fields = ("session_id", "role", "content", "created_at")

    @admin.display(description="内容预览")
    def content_preview(self, obj):
        return obj.content[:60]
