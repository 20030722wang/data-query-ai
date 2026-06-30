# DataQuery AI — 自然语言转 SQL 智能查询助手

基于 **LangGraph + FastAPI + Vue 3**，通过元数据 RAG（向量检索 + ES 关键词检索）增强 LLM，将自然语言自动翻译为 SQL 并执行，返回查询结果。

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM 编排 | LangGraph（状态图多节点流水线） |
| 后端框架 | FastAPI（SSE 流式响应） |
| 前端 | Vue 3 + Vite |
| 元数据存储 | MySQL 8.0 |
| 向量检索 | Qdrant |
| 关键词检索 | Elasticsearch + IK 分词 |
| Embedding | BAAI/bge-large-zh-v1.5（TEI 服务） |
| 包管理 | uv（也提供 requirements.txt） |
| 基础设施 | Docker Compose |

## 项目结构

```
├── app/                    # 后端 Python
│   ├── agent/              #   LangGraph 图 + 节点（12 个节点）
│   │   └── nodes/          #     extract_keywords → recall → filter → generate → validate → run
│   ├── api/                #   FastAPI 路由 + 依赖注入
│   ├── clients/            #   外部服务客户端 (MySQL, ES, Qdrant, Embedding)
│   ├── conf/               #   配置加载 (OmegaConf)
│   ├── core/               #   日志 + 请求上下文
│   ├── entities/           #   领域实体 dataclass
│   ├── models/             #   SQLAlchemy ORM
│   ├── prompt/             #   Prompt 模板加载器
│   ├── repositories/       #   数据访问层 (MySQL / ES / Qdrant)
│   ├── scripts/            #   元数据导入脚本
│   └── services/           #   业务服务
├── frontend/               # Vue 3 前端 (Vite)
│   └── src/
│       └── App.vue         #   聊天界面 (SSE 流式渲染)
├── conf/                   # 配置文件 (YAML)
├── prompts/                # LLM Prompt 模板 (.prompt)
├── docker/                 # Docker Compose + 初始化 SQL + 模型目录
├── scripts/                # 工具脚本（模型下载等）
├── main.py                 # FastAPI 入口
├── pyproject.toml          # Python 项目配置 (uv)
└── requirements.txt        # pip fallback
```

## 快速开始

### 环境要求

- **Python >= 3.12** + [uv](https://docs.astral.sh/uv/)（或 pip）
- **Node.js >= 18**（仅前端）
- **Docker Desktop**

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd dataquery-ai
```

### 2. 下载 Embedding 模型（首次，约 1.3GB）

```bash
python scripts/download_model.py
```

> 模型文件 `pytorch_model.bin` 被 gitignore 了（GitHub 限制 100MB），需手动下载一次。

### 3. 启动基础设施

```bash
cd docker
docker compose up -d
```

启动 MySQL、Elasticsearch、Qdrant、Kibana、Embedding 服务。首次拉取镜像可能需要几分钟。

> 端口冲突？编辑 `docker/.env` 修改映射端口。

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**至少填入 `LLM_API_KEY`**。其余变量有默认值，开箱即用。

### 5. 安装依赖 + 导入元数据

```bash
# 方式一：uv（推荐，更快）
uv sync
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yml

# 方式二：pip
pip install -r requirements.txt
python -m app.scripts.build_meta_knowledge -c conf/meta_config.yml
```

> 国内用户若下载慢，取消 `pyproject.toml` 末尾清华镜像的注释，或 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`。

### 6. 启动后端

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. 启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

访问 **http://localhost:5173**，输入自然语言查询即可。

### 生产部署

```bash
cd frontend && npm run build
# 将 frontend/dist/ 部署到 Nginx，/api 反向代理到 localhost:8000
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/query` | 提交自然语言查询，返回 SSE 流 |

请求体：
```json
{ "query": "统计华北地区的销售总额" }
```

响应为 Server-Sent Events 流，事件类型：
- `progress` — 节点执行进度
- `result` — 最终结果（含 SQL + 数据）
- `error` — 错误信息

## 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | (必填) | LLM API Key |
| `LLM_MODEL` | `gpt-4.1` | 模型名称 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API 地址，兼容任意 OpenAI 风格服务 |
| `DB_META_USER` | `atguigu` | 元数据库用户 |
| `DB_META_PASSWORD` | `Atguigu.123` | 元数据库密码 |
| `DB_DW_USER` | `atguigu` | 数据仓库用户 |
| `DB_DW_PASSWORD` | `Atguigu.123` | 数据仓库密码 |
| `PYTHONIOENCODING` | `utf-8` | Windows 中文不乱码 |

## 故障排查

### 中文输出乱码
`.env` 中确保 `PYTHONIOENCODING=utf-8`，且终端使用 UTF-8 编码。

### pip 安装失败（safetensors / torch 超时）
网络问题，重试几次，或使用国内镜像：
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### Docker 服务启动失败
确保 Docker Desktop 正在运行，端口不被占用。修改 `docker/.env` 可更换端口。

### Embedding 服务报错 "model not found"
模型未下载，运行 `python scripts/download_model.py`。

### Qdrant 连接被拒
Qdrant 启动较慢，等几秒后重试。

## License

MIT
