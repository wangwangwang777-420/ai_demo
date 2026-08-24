"""
视图层：
- index     渲染 IM 风格聊天页（前端原生 HTML/CSS/JS）
- chat_api  POST {message, session_id}，调用大模型并以 SSE 流式返回
"""
import json
import logging
import uuid

from django.conf import settings
from django.db import close_old_connections
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .llm import LLMClient, LLMError
from .models import Message

logger = logging.getLogger(__name__)


def index(request):
    """渲染聊天页面"""
    return render(request, "chat/index.html")


@csrf_exempt
def chat_api(request):
    """
    流式对话接口。

    请求体:  {"message": "你好", "session_id": "sess_xxx"}
    返回:    text/event-stream，逐片推送 data: {json}\n\n，结尾 data: [DONE]

    csrf_exempt 仅用于演示；生产环境应改用 Token / Session 登录等鉴权方案，
    且接口应限制访问频率，避免被刷掉 API 额度。
    """
    # ---------- 1. 请求校验 ----------
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST 请求"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "请求体不是合法的 JSON"}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "消息不能为空"}, status=400)

    session_id = (body.get("session_id") or "").strip()
    if not session_id:
        # 前端正常会传 session_id；缺失时兜底生成，保证接口不中断
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

    # ---------- 2. 前置校验：未配置 API Key 直接给明确错误 ----------
    if not settings.LLM_API_KEY:
        return JsonResponse(
            {
                "error": (
                    "未配置 LLM_API_KEY。请复制 .env.example 为 .env，"
                    "填入你的 DeepSeek（或其它供应商）API Key 后重启服务。"
                )
            },
            status=500,
        )

    # ---------- 3. 读取同一会话最近 N 条历史（多轮记忆） ----------
    # 倒序取最近 N 条，再反转成时间正序，得到 [最早 -> 最近]
    history_qs = (
        Message.objects.filter(session_id=session_id)
        .order_by("-created_at", "-id")
        [: settings.LLM_MAX_HISTORY]
    )
    history = [(m.role, m.content) for m in reversed(list(history_qs))]

    # 先落库用户消息（这样即使 AI 回复失败，用户提问也留下了记录）
    Message.objects.create(session_id=session_id, role="user", content=message)

    # ---------- 4. SSE 流式生成 ----------
    def sse_stream():
        """
        生成器：被 StreamingHttpResponse 逐块推送给客户端。
        运行在响应线程中，故在开头/结尾关闭旧数据库连接，
        避免连接跨线程复用导致 "database is locked" 之类的问题。
        """
        close_old_connections()
        llm = LLMClient()
        messages = llm.build_messages(history, message)
        full_answer = ""
        error_msg = None

        try:
            for delta in llm.stream_chat(messages):
                full_answer += delta
                payload = json.dumps({"delta": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"  # SSE 事件格式
            # 正常结束标记
            yield "data: [DONE]\n\n"
        except LLMError as exc:
            error_msg = str(exc)
            logger.exception("LLM streaming failed")
            payload = json.dumps({"error": error_msg}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # 落库助手消息：正常完成 / 出错 / 前端中断三种情况都尽量保存
            if error_msg is not None:
                full_answer = f"[系统提示] {error_msg}"
            if full_answer.strip():
                Message.objects.create(
                    session_id=session_id, role="assistant", content=full_answer
                )
            close_old_connections()

    response = StreamingHttpResponse(
        sse_stream(), content_type="text/event-stream; charset=utf-8"
    )
    # 禁用代理/浏览器缓冲，保证每片内容即时推送（SSE 的关键）
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
