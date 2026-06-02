# Mini-Rag

基于 LangChain 1.x 框架构建的轻量级 RAG（Retrieval-Augmented Generation）系统，支持多格式文档解析、向量存储、智能问答，并提供完整的用户体系与知识库管理。

## 项目介绍

Mini-Rag 是一个开箱即用的私有化知识库问答系统，核心特性包括：

- **多格式文档解析** — 支持 PDF、Word、PPT、Excel、CSV、TXT、Markdown 等常见文件格式
- **灵活的文档切割** — 提供递归字符分割、字符分割、Markdown 标题分割三种方式，可自定义块大小与重叠长度
- **向量存储与检索** — 基于 ChromaDB 实现文档向量化持久存储与相似度检索，可配置嵌入维度
- **RAG 流式智能问答** — 检索相关知识片段后由 LLM 流式生成回答，支持引用来源展示
- **微信风格对话界面** — AI 消息居左气泡，用户消息居右气泡，markdown 格式正确渲染
- **后台嵌入任务** — 大批量文档导入通过后台线程处理，不阻塞用户其他操作
- **多用户体系** — 基于 SQLAlchemy ORM + bcrypt 的用户注册/登录，支持管理员与普通用户角色
- **数据库双引擎** — 同时兼容 SQLite（开箱即用）与 MySQL（生产环境），通过环境变量切换
- **聊天历史持久化** — 用户与 AI 的对话自动保存到数据库，刷新页面后可恢复最近会话
- **知识库管理** — 创建/删除/搜索知识库、单文件上传或指定目录批量导入、查看文件与向量统计
- **友好 Web 界面** — 基于 Streamlit 构建的居中登录页与侧边栏导航布局

## 项目架构

```
Mini-Rag/
├── app.py                          # 应用主入口，页面路由与会话管理
├── config.py                       # 全局配置（API、路径、数据库类型等）
├── .env                            # 环境变量配置文件
│
├── docAnalysis/                    # 文档加载模块
│   ├── __init__.py
│   └── loader.py                   # DocumentLoader — 多格式文档加载器
│
├── docSplitter/                    # 文档切割模块
│   ├── __init__.py
│   └── splitter.py                 # DocumentSplitter — 文档分割器
│
├── docEmbedding/                   # 文档嵌入与检索模块
│   ├── __init__.py
│   ├── embedding.py                # EmbeddingManager — 向量存储、流式检索、RAG 链
│   └── job_manager.py              # 后台嵌入任务管理器（线程 + 进度持久化）
│
├── db/                             # 数据库模块
│   ├── __init__.py
│   └── database.py                 # Database — SQLAlchemy ORM，同时支持 SQLite 与 MySQL
│
├── ui/                             # Streamlit 界面模块
│   ├── __init__.py
│   ├── login.py                    # 居中布局的登录/注册页面
│   ├── knowledge_base.py           # 知识库管理页面（搜索、删除确认、后台导入）
│   ├── chat.py                     # 微信风格 RAG 智能问答页面（流式输出）
│   └── user_manage.py              # 用户管理页面（仅管理员可见）
│
└── data/                           # 运行时数据目录（自动创建）
    ├── mini_rag.db                 # SQLite 数据库文件
    ├── chroma_db/                  # ChromaDB 向量持久化存储
    ├── embedding_jobs.json         # 后台嵌入任务状态持久化
    └── uploads/                    # 用户上传文件存储
```

### 核心模块说明

| 模块 | 类 / 文件 | 职责 |
|------|----------|------|
| `docAnalysis/loader.py` | `DocumentLoader` | 根据文件扩展名自动选择加载器，支持单文件和目录批量加载 |
| `docSplitter/splitter.py` | `DocumentSplitter` | 提供 recursive / character / markdown_header 三种分割策略 |
| `docEmbedding/embedding.py` | `EmbeddingManager` | 管理 OpenAI Embeddings + ChromaDB 向量存储、流式 RAG 检索、引用来源提取 |
| `docEmbedding/job_manager.py` | `JobManager` | 单例 + 守护线程 + 任务状态持久化，实现后台嵌入任务不阻塞 UI |
| `db/database.py` | `Database` | 基于 SQLAlchemy ORM，同时支持 SQLite 与 MySQL，管理用户/知识库/文件/聊天历史四张表 |
| `ui/login.py` | `render_login_page` | 居中卡片式登录/注册页 |
| `ui/chat.py` | `render_chat_page` | 微信风格聊天气泡 + 流式生成 + 引用来源展示 |
| `ui/knowledge_base.py` | `render_knowledge_base_page` | 知识库 CRUD + 后台目录批量导入 + 实时任务进度 |
| `ui/user_manage.py` | `render_user_manage_page` | 用户搜索、删除、密码修改（仅管理员） |

### 数据库表结构

数据库层基于 **SQLAlchemy ORM**，可在 SQLite（默认）与 MySQL 之间无缝切换。

**users（用户表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| username | VARCHAR(64) | 用户名，唯一 |
| password_hash | VARCHAR(255) | bcrypt 加密后的密码 |
| role | VARCHAR(20) | 角色：`admin` / `user` |
| created_at | DATETIME | 创建时间 |

**knowledge_bases（知识库表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| name | VARCHAR(128) | 知识库名称 |
| description | TEXT | 知识库描述 |
| splitter_type | VARCHAR(32) | 分割方式：`recursive` / `character` / `markdown_header` |
| chunk_size | INTEGER | 块大小 |
| chunk_overlap | INTEGER | 块重叠 |
| user_id | INTEGER | 所属用户 ID |
| created_at | DATETIME | 创建时间 |

**kb_files（知识库文件表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| kb_id | INTEGER | 所属知识库 ID |
| file_name | VARCHAR(255) | 文件名 |
| file_path | VARCHAR(512) | 文件存储路径 |
| file_type | VARCHAR(32) | 文件类型 |
| chunk_count | INTEGER | 切割后的文本块数量 |
| created_at | DATETIME | 创建时间 |

**chat_history（聊天历史表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| user_id | INTEGER | 用户 ID |
| kb_name | VARCHAR(255) | 所属知识库名称 |
| role | VARCHAR(50) | `user` / `assistant` |
| content | TEXT | 消息内容 |
| sources | TEXT | JSON 数组，AI 回复的引用来源 |
| created_at | DATETIME | 创建时间 |

## 使用说明

### 环境要求

- Python 3.10+
- 虚拟环境 `.venv`（已配置）

### 启动应用

```bash
# 激活虚拟环境并启动
.venv\Scripts\streamlit run app.py --server.headless true
```

启动后浏览器访问 `http://localhost:8501`。

### 默认管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |

> 首次启动时系统会自动创建管理员账号，建议登录后立即修改密码。

### 操作流程

1. **登录系统** — 在居中卡片页使用管理员账号登录，或切换到「注册」标签创建新用户
2. **创建知识库** — 进入「知识库管理」→「创建知识库」，填写名称、描述、选择分割方式和参数
3. **上传文档** — 进入「知识库管理」→「上传文件」，选择目标知识库后：
   - **上传文件**：直接选择本地文件上传，实时进度圈显示处理过程
   - **指定目录**：输入服务器上目录的绝对路径，系统扫描后点击 `🚀 开始嵌入` 启动后台线程处理，**处理过程中可切换到其他功能继续操作**
4. **智能问答** — 进入「RAG 问答」，自动恢复最近一次会话的知识库与历史消息：
   - AI 回复**流式输出**，2-3 秒即可看到首个字
   - 微信风格布局：AI 居左白色气泡，用户居右绿色气泡
   - 消息内容以 markdown 格式正确渲染（代码块、列表、表格等）
   - 每次回答下方直接展示**引用来源**（文件 + 页码）
5. **用户管理**（仅管理员）— 进入「用户管理」，可搜索/删除用户、修改密码

### 支持的文件格式

| 扩展名 | 文件类型 | 说明 |
|--------|----------|------|
| `.pdf` | PDF | 使用 PyPDFLoader 解析 |
| `.docx` / `.doc` | Word | 使用 Docx2txtLoader 解析 |
| `.pptx` / `.ppt` | PowerPoint | 使用 python-pptx 解析 |
| `.xlsx` / `.xls` | Excel | 使用 UnstructuredExcelLoader 解析 |
| `.csv` | CSV | 使用 CSVLoader 解析 |
| `.txt` | 纯文本 | 使用 TextLoader 解析 |
| `.md` / `.markdown` | Markdown | 使用 UnstructuredMarkdownLoader 解析 |

### 分割方式说明

| 分割方式 | 说明 | 适用场景 |
|----------|------|----------|
| 递归字符分割（推荐） | 按分隔符层级递归分割，支持中英文标点 | 通用文档 |
| 字符分割 | 按换行符分割 | 结构简单的文本 |
| Markdown 标题分割 | 按 `#` / `##` / `###` 标题层级分割 | Markdown 文档 |

## 配置

### 环境变量

编辑项目根目录下的 `.env` 文件进行配置：

```env
# ========== LLM / Embedding 配置 ==========
# OpenAI API Key（必填）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# OpenAI API 地址（支持兼容接口，如 Azure OpenAI、本地部署、国内代理等）
OPENAI_API_BASE=https://api.openai.com/v1

# 对话模型
LLM_MODEL=gpt-3.5-turbo

# 嵌入模型
EMBEDDING_MODEL=text-embedding-ada-002

# 嵌入向量维度（可选，仅 text-embedding-3-* 系列支持；设为 0 表示使用模型默认维度）
EMBEDDING_DIMENSIONS=0

# ========== 数据库配置 ==========
# 数据库类型：sqlite（默认，开箱即用）/ mysql（生产环境）
DB_TYPE=sqlite

# MySQL 配置（仅当 DB_TYPE=mysql 时生效）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=mini_rag
```

### 嵌入向量维度优化

`text-embedding-3-large` / `text-embedding-3-small` 支持自定义输出维度，可在 `OPENAI_API_BASE` 兼容的接口中使用：

```env
EMBEDDING_DIMENSIONS=1024
```

| 维度 | 说明 |
|------|------|
| `0`（默认） | 使用模型原始维度（3-large: 3072, 3-small: 1536, ada-002: 1536） |
| 正整数 | 自定义维度，可减少存储空间、加速检索；需重新导入已有数据 |

### 兼容第三方 API

本项目支持所有兼容 OpenAI 接口的服务，只需修改 `OPENAI_API_BASE` 即可：

```env
# Azure OpenAI
OPENAI_API_BASE=https://your-resource.openai.azure.com/openai/deployments/your-deployment

# 本地部署（如 Ollama、vLLM）
OPENAI_API_BASE=http://localhost:8000/v1

# 国内代理服务
OPENAI_API_BASE=https://your-proxy.com/v1
```

系统会自动为缺失 `/v1` 后缀的地址补全。

### 数据库切换

通过 `DB_TYPE` 环境变量在 SQLite 与 MySQL 之间切换：

```env
# 使用 SQLite（默认，无需额外配置）
DB_TYPE=sqlite

# 使用 MySQL
DB_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=mini_rag
```

> 切换数据库后需提前创建对应的库与字符集（推荐 `utf8mb4`），系统会自动建表。

### 数据存储路径

数据存储路径在 `config.py` 中定义，默认位于项目根目录的 `data/` 下：

| 配置项 | 默认路径 | 说明 |
|--------|----------|------|
| `DB_PATH` | `data/mini_rag.db` | SQLite 数据库文件 |
| `CHROMA_PERSIST_DIR` | `data/chroma_db/` | ChromaDB 向量存储目录 |
| `UPLOAD_DIR` | `data/uploads/` | 上传文件存储目录 |

## 维护

### 依赖管理

```bash
# 安装依赖
.venv\Scripts\pip install -r requirements.txt
```

主要依赖清单：

| 包名 | 用途 |
|------|------|
| `langchain` | LangChain 核心框架 |
| `langchain-openai` | OpenAI 模型集成 |
| `langchain-chroma` | ChromaDB 向量存储集成 |
| `langchain-community` | 社区文档加载器 |
| `langchain-core` | 核心抽象（Document、PromptTemplate 等） |
| `chromadb` | ChromaDB 向量数据库 |
| `streamlit` | Web 界面框架 |
| `sqlalchemy` | ORM 抽象层，兼容 SQLite 与 MySQL |
| `pymysql` | MySQL 驱动（仅在 MySQL 模式下需要） |
| `python-docx` | Word 文档解析 |
| `python-pptx` | PPT 文档解析 |
| `openpyxl` | Excel 文档解析 |
| `pypdf` | PDF 文档解析 |
| `bcrypt` | 密码加密 |
| `python-dotenv` | 环境变量加载 |

### 数据备份

```bash
# 备份 SQLite 数据库
copy data\mini_rag.db data\mini_rag.db.bak

# 备份 ChromaDB 向量数据
xcopy /E /I data\chroma_db data\chroma_db_bak
```

> MySQL 环境下请使用 `mysqldump` 备份对应数据库。

### 数据清理

- **删除知识库**：在知识库管理页面点击 `🗑️` 按钮确认删除，系统会同时清理 ChromaDB 中的对应 collection、SQLite 中的文件记录与聊天历史
- **重置数据库**：删除 `data/mini_rag.db` 文件，重启应用后会自动重建（注意：这会丢失所有用户、知识库、聊天历史）
- **清理向量数据**：删除 `data/chroma_db/` 目录，重启后知识库需要重新上传文件
- **清理后台任务**：删除 `data/embedding_jobs.json` 文件

### 常见问题

**Q: 启动后页面空白或报错？**

检查 `.env` 文件中 `OPENAI_API_KEY` 是否已正确填写，以及 `OPENAI_API_BASE` 是否可访问。

**Q: 上传文件后向量数为 0？**

确认文件格式在支持列表中，检查文件内容是否为空或无法解析。查看终端日志获取详细错误信息。

**Q: 问答时 AI 回复很慢？**

启用流式输出后首个 token 通常 2-3 秒即可出现。若整体生成慢，可尝试：
- 减小 `top_k`（侧边栏「检索文档数」）
- 在 `.env` 中调小 `EMBEDDING_DIMENSIONS`
- 切换到更轻量的 `LLM_MODEL`

**Q: 对话内容显示为源码（如 `</div>`）？**

项目已修复此问题，AI 回复使用 `st.chat_message` 原生渲染并配合 `st.markdown` 正确解析 markdown 格式。

**Q: 后台嵌入任务卡在某个文件？**

检查对应文件是否损坏或体积过大，可手动在文件管理器中删除后重新上传。

**Q: 如何修改默认端口？**

启动时指定端口参数：
```bash
.venv\Scripts\streamlit run app.py --server.port 8502 --server.headless true
```

**Q: 切换到 MySQL 后启动失败？**

确认 `pymysql` 已安装：`pip install pymysql`，并提前在 MySQL 中创建好 `mini_rag` 库（字符集 `utf8mb4`）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | LangChain 1.x |
| LLM | OpenAI GPT（可替换为兼容接口，支持流式输出） |
| Embedding | OpenAI Embeddings（支持自定义维度） |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite / MySQL（SQLAlchemy ORM 抽象） |
| 密码加密 | bcrypt |
| Web 界面 | Streamlit |
| 文档解析 | PyPDF / python-docx / python-pptx / openpyxl / Unstructured |
| 并发模型 | threading 守护线程 + JSON 状态持久化 |
