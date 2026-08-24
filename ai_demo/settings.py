"""
Django 配置文件。

核心设计：环境变量隔离。
- 用 python-dotenv 读取项目根目录的 .env，API Key / 密钥一律不写死在代码里；
- 所有大模型相关配置集中在这里，切换供应商（DeepSeek / OpenAI / 通义千问 / 智谱）
  只需改 LLM_API_BASE 与 LLM_MODEL 两个环境变量；
- DATABASES 开发用 SQLite，注释里给出切换 MySQL 的写法，ORM 代码无需改动。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（文件不存在时静默跳过，此时 LLM_API_KEY 等保持为空）
# override=True：.env 里的变量始终覆盖进程已有环境变量，
# 避免“启动终端里曾 set 过 LLM_API_KEY 空值导致改 .env 无效”的坑。
load_dotenv(BASE_DIR / ".env", override=True)


def _env_bool(key: str, default: bool = False) -> bool:
    """把 .env 里的字符串转成布尔值，避免手写 '1'/'true' 等格式不一致"""
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ---------------- 基础配置 ----------------
# SECURITY WARNING: 生产环境务必通过 .env 里的 DJANGO_SECRET_KEY 覆盖
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-2#8r(6z!-7k@demo-only-key-never-use-in-production",
)
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 本项目业务应用（对话）
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ai_demo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # APP_DIRS=True：自动去每个 app 的 templates/ 目录找模板
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ai_demo.wsgi.application"
ASGI_APPLICATION = "ai_demo.asgi.application"

# ---------------- 数据库 ----------------
# 开发环境使用 SQLite，零配置开箱即用。
# 切到 MySQL 时：改 ENGINE / NAME / USER / PASSWORD / HOST / PORT 即可，
# 因为业务代码全部走 Django ORM（无原生 SQL），无需改动 models。
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # -------- MySQL 切换示例（生产环境）--------
        # "ENGINE": "django.db.backends.mysql",
        # "NAME": os.getenv("MYSQL_DB", "ai_demo"),
        # "USER": os.getenv("MYSQL_USER", "root"),
        # "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        # "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        # "PORT": os.getenv("MYSQL_PORT", "3306"),
    }
}

# 国际化 / 时区
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ---------------- 静态文件 ----------------
STATIC_URL = "static/"

# Django 默认主键类型
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------- 大模型配置（OpenAI 兼容 Chat Completions） ----------------
# 统一走 POST {LLM_API_BASE}/chat/completions 的流式接口。
# 切换供应商只需改两个变量：
#   DeepSeek : base=https://api.deepseek.com/v1            model=deepseek-chat
#   OpenAI   : base=https://api.openai.com/v1              model=gpt-4o-mini
#   通义千问 : base=https://dashscope.aliyuncs.com/compatible-mode/v1  model=qwen-plus
#   智谱 GLM : base=https://open.bigmodel.cn/api/paas/v4   model=glm-4-flash
LLM_API_KEY = os.getenv("LLM_API_KEY", "")  # 未配置时接口会返回明确错误而非崩溃
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_SYSTEM_PROMPT = os.getenv(
    "LLM_SYSTEM_PROMPT",
    "你是一个乐于助人的 AI 助手，请用简洁、清晰、有条理的中文回答问题。",
)
# 网络超时（秒）：connect_timeout, read_timeout
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
# 携带到上下文的最近 N 条历史消息（实现多轮记忆）
LLM_MAX_HISTORY = int(os.getenv("LLM_MAX_HISTORY", "10"))

# 预留：RAG 知识库开关。置为 true 后，llm.build_messages 会在系统提示词里
# 注入检索到的资料片段（见 chat/llm.py 的 RAG 注入点注释）。
RAG_ENABLED = _env_bool("RAG_ENABLED", False)
