# AI 对话助手（Django + 大模型）

一个基于 **Django 4/5 + OpenAI 兼容大模型接口** 的流式 AI 问答 Demo，用于简历项目展示。

- 类微信/IM 的聊天界面，前端 **原生 HTML/CSS/JS**，零框架依赖
- 后端 **SSE（text/event-stream）** 流式返回，前端 `fetch + ReadableStream` 逐片消费
- "打字机"逐字渲染效果，支持流式中断（停止按钮）
- Django ORM 持久化每一轮对话，携带最近 N 条历史实现 **多轮记忆**
- 系统提示词、API Key 全部通过 `.env` 注入，可 **一键切换 DeepSeek / OpenAI / 通义千问 / 智谱**
- 预留 **RAG 知识库注入点**（见 `chat/llm.py` 注释）
- 完善异常处理：未配置 Key、空消息、HTTP 非 200、超时、断流均有友好返回

---

## 目录结构

```
ai_demo/
├── manage.py
├── ai_demo/                  # 项目配置
│   ├── settings.py           # 环境变量隔离 + LLM 配置 + 可切 MySQL 的 DATABASES
│   ├── urls.py / wsgi.py / asgi.py
├── chat/                     # 业务应用
│   ├── models.py             # Message 模型（session_id / role / content / created_at）
│   ├── views.py              # index 页面 + chat_api 流式接口
│   ├── llm.py                # 大模型客户端封装（stream_chat 生成器 + 异常处理）
│   ├── urls.py / admin.py / migrations/
│   └── templates/chat/index.html
├── requirements.txt
├── .env.example              # 环境变量模板
└── README.md
```

## 快速开始

需要 **Python 3.10+**。

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
# Windows (cmd):   venv\Scripts\activate
# Windows (git bash): source venv/Scripts/activate
# Linux/macOS:    source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 生成环境配置并填入 API Key
cp .env.example .env
#   编辑 .env，填入 LLM_API_KEY=（DeepSeek 等平台申请）

# 4. 建表
python manage.py makemigrations chat
python manage.py migrate

# 5. 启动
python manage.py runserver
```

浏览器打开 <http://127.0.0.1:8000/> 即可对话。

> **没有 API Key 也可以跑**：页面能正常打开，发送消息时接口会返回明确的错误提示（"未配置 LLM_API_KEY…"），不会崩溃——这本身就是一个异常处理的设计点，面试可以讲。

## 如何切换模型供应商

所有供应商都走 **OpenAI 兼容的 `/chat/completions`** 接口，改两个环境变量即可：

| 供应商   | LLM_API_BASE                                        | LLM_MODEL      |
|----------|-----------------------------------------------------|----------------|
| DeepSeek | `https://api.deepseek.com/v1`                       | `deepseek-chat` |
| OpenAI   | `https://api.openai.com/v1`                         | `gpt-4o-mini`  |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`    |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4`              | `glm-4-flash`  |

修改 `.env` 后重启 `runserver` 即可。

## 接口说明

### `POST /api/chat`

请求体：

```json
{
  "message": "你好，介绍一下你自己",
  "session_id": "sess_xxxx"
}
```

返回 `text/event-stream`，逐片推送：

```
data: {"delta": "你"}
data: {"delta": "好"}
data: [DONE]
```

前端约定：`{delta: string}` 表示文本增量，`{error: string}` 表示错误事件。

多轮记忆：后端按 `session_id` 从 `chat_message` 表读取最近 `LLM_MAX_HISTORY` 条历史，
与系统提示词、当前消息拼成上下文发给模型。前端把 `session_id` 存在 `localStorage`，
刷新页面后 AI 仍然记得之前的对话。

## RAG 预留说明

`chat/llm.py` 中预留了两个注入点：

1. `_build_system_prompt()`：当 `settings.RAG_ENABLED = true` 时，会调用
   `retrieve_documents()` 把检索到的资料片段拼进系统提示词；
2. `retrieve_documents()`：占位方法，后续接入向量库 / 全文检索 / 搜索 API 即可，
   流式调用逻辑（`stream_chat`）完全不用改。

## 切换到 MySQL

开发用 SQLite，生产切 MySQL 只需改 `ai_demo/settings.py` 里 `DATABASES` 一处
（注释里已给出示例配置），业务代码因为全部走 ORM 无需改动。注意需安装
`mysqlclient`（或 `pymysql`）。

## 简历中可以怎么写

**项目：AI 对话助手 —— Django 流式 LLM 应用（多轮记忆 + RAG 预留）**

- 使用 Django（MVT 架构）开发 Web 应用，实现 IM 风格聊天页面与 `POST /api/chat` 流式接口
- 基于 OpenAI 兼容 `chat/completions` 接口，用 `requests.stream=True + iter_lines` 解析 SSE，
  通过 `StreamingHttpResponse` 逐片推送，前端 `fetch + ReadableStream` 消费并实现打字机效果
- 设计 `Message` 模型（session_id / role / content / created_at），按会话读取最近 N 条历史
  拼装上下文，实现多轮记忆；ORM 全字段索引，方便切换 MySQL
- 环境变量隔离：`python-dotenv` 读取 `.env`，API Key / 系统提示词 / 供应商地址集中配置，
  支持 DeepSeek / OpenAI / 通义千问 / 智谱一键切换
- 预留 RAG 注入点（`build_messages` / `retrieve_documents`），为接入知识库问答做准备
- 异常处理完善：未配置 Key、HTTP 非 200、网络超时、前端断流均有友好返回，接口不崩溃

面试可延展的话题：SSE 与 WebSocket 的取舍、StreamingHttpResponse 与线程内数据库连接管理
（`close_old_connections`）、如何做限流与鉴权、RAG 的切分/召回策略、SQLite 到 MySQL 的迁移注意点。

## License

仅供学习 / 简历展示使用。
