"""
数据模型：对话消息持久化。

设计要点：
- session_id 区分不同会话，配合组合索引 (session_id, created_at) 实现
  "读取同一会话最近 N 条历史" 的高效查询（多轮记忆的数据基础）；
- 全部使用 Django ORM 定义，切换 SQLite -> MySQL 时无需改动任何业务代码；
- 字段均为标准 Django 字段，方便日后扩展（如新增 tokens、status 等列）。
"""
from django.db import models


class Message(models.Model):
    """一轮对话中的一条消息"""

    # 会话标识：前端生成并透传，同一 session_id 的消息属于同一个多轮会话
    session_id = models.CharField(max_length=64, db_index=True, verbose_name="会话ID")

    # 消息角色：user（用户提问）/ assistant（AI 回复）/
    # system（预留：系统或 RAG 注入的上下文，demo 中存于提示词而非表中）
    role = models.CharField(max_length=16, choices=[
        ("user", "用户"),
        ("assistant", "AI 助手"),
        ("system", "系统"),
    ], verbose_name="角色")

    # 消息正文：内容可能较长，用 TextField
    content = models.TextField(verbose_name="内容")

    # 创建时间：auto_now_add 写入后不可再改，同时用作历史排序字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at", "id"]  # 默认按时间正序，方便直接取历史
        verbose_name = "对话消息"
        verbose_name_plural = "对话消息"
        # 组合索引：按会话 + 时间范围过滤历史消息时走索引，避免全表扫描
        indexes = [
            models.Index(fields=["session_id", "created_at"], name="idx_session_time"),
        ]

    def __str__(self):
        return f"[{self.session_id}] {self.role}: {self.content[:30]}"
