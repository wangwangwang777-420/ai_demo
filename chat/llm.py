"""
大模型客户端封装（OpenAI 兼容 Chat Completions 接口）。

核心能力：
- 用 requests 的 stream=True + iter_lines 逐行解析 SSE 流，对外暴露
  stream_chat() 生成器，逐片 yield 文本增量；
- 统一处理：未配置 API Key / HTTP 非 200 / 网络超时 / 连接失败 / 流中断，
  抛出的 LLMError.message 均为可直接展示给用户的中文提示；
- 预留 RAG 知识库注入点（build_messages 与 _build_system_prompt）。
"""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """统一的大模型调用异常，message 为可直接展示给用户的中文提示"""


class LLMClient:
    """封装 OpenAI 兼容的 /chat/completions 流式接口"""

    def __init__(self, api_key=None, api_base=None, model=None, timeout=None):
        # 未显式传入时，从 Django settings（即 .env）读取
        self.api_key = api_key or settings.LLM_API_KEY
        self.api_base = (api_base or settings.LLM_API_BASE).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT
        self.system_prompt = settings.LLM_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # 上下文组装
    # ------------------------------------------------------------------
    def build_messages(self, history, user_content=None):
        """
        组装发给模型的 messages 列表：
            [system 提示词] + 最近 N 条历史 + 当前用户问题

        :param history: 由 ORM 读出的 [(role, content), ...]，时间正序
        :param user_content: 当前用户消息（可为空，仅用于单元测试/拼接）
        """
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        # 多轮记忆：把历史消息按时间顺序追加进上下文
        messages.extend(
            {"role": role, "content": content} for role, content in history
        )

        if user_content:
            messages.append({"role": "user", "content": user_content})
        return messages

    def _build_system_prompt(self):
        """
        RAG 预留注入点：
        未来接入知识库时，只需在此处把检索命中的文档片段拼进系统提示词
        （例如 "请优先参考以下资料作答：\n{retrieved}"），
        流式调用逻辑（stream_chat）完全不用改。
        """
        if getattr(settings, "RAG_ENABLED", False):
            retrieved = self.retrieve_documents()
            if retrieved:
                return f"{self.system_prompt}\n\n【参考资料】\n{retrieved}"
        return self.system_prompt

    def retrieve_documents(self):
        """占位：RAG 文档检索。后续可接入向量库 / 全文检索 / 外部搜索 API。"""
        return ""

    # ------------------------------------------------------------------
    # 流式调用
    # ------------------------------------------------------------------
    def stream_chat(self, messages):
        """
        调用大模型并以生成器形式逐片返回文本增量。

        :yield: str，每个元素是模型返回的一小段文本
        :raises LLMError: 调用失败时的友好提示
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,  # 关键：请求模型开启流式返回
            "temperature": 0.7,
        }
        logger.info("LLM request -> %s model=%s", url, self.model)

        # ---- 发请求：统一捕获网络层异常，转成友好提示 ----
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,  # 关键：不一次性读入整个响应体
                # (connect_timeout, read_timeout)：读取超时防止流卡死
                timeout=(self.timeout, self.timeout),
            )
        except requests.exceptions.Timeout as exc:
            raise LLMError(f"请求模型超时（>{self.timeout}s），请稍后重试。") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMError("无法连接模型服务，请检查网络或 LLM_API_BASE 配置。") from exc
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"请求模型服务失败：{exc}") from exc

        # ---- HTTP 状态非 200：尝试从响应体提取错误信息 ----
        if resp.status_code != 200:
            try:
                err = resp.json().get("error", {}).get("message", resp.text[:200])
            except ValueError:
                err = resp.text[:200]
            logger.error("LLM http error: %s %s", resp.status_code, err)
            raise LLMError(f"模型服务返回错误（HTTP {resp.status_code}）：{err}")

        # ---- 解析 SSE 流：逐行读取，识别 "data:" 行 ----
        try:
            for line in resp.iter_lines(decode_unicode=True):
                # SSE 每事件形如 "data: {json}\n\n"，忽略空行/注释行
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":  # 流结束标记
                    break
                try:
                    chunk = json.loads(data)
                    # OpenAI 兼容格式：choices[0].delta.content
                    delta = chunk["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError) as exc:
                    # 个别脏数据直接跳过，不影响整体流
                    logger.warning("skip malformed SSE chunk: %r", data)
                    continue
                if delta:
                    yield delta
        finally:
            resp.close()  # 无论正常结束还是异常退出都释放连接
