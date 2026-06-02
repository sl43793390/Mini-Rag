# Mini-Rag

A lightweight RAG (Retrieval-Augmented Generation) system built on LangChain 1.x, supporting multi-format document parsing, vector storage, intelligent Q&A, with a complete user system and knowledge base management.

## Introduction

Mini-Rag is an out-of-the-box, self-hosted knowledge base Q&A system. Core features include:

- **Multi-format Document Parsing** — Supports PDF, Word, PPT, Excel, CSV, TXT, Markdown and other common file formats
- **Flexible Document Splitting** — Provides three splitting strategies: recursive character, character, and Markdown header; chunk size and overlap are configurable
- **Vector Storage & Retrieval** — Document vectorization, persistent storage, and similarity search powered by ChromaDB; embedding dimensions are configurable
- **Streaming RAG Q&A** — Retrieves relevant context first, then generates answers via LLM with streaming output; reference sources are shown
- **WeChat-style Chat UI** — AI messages on the left, user messages on the right; Markdown content is rendered correctly
- **Background Embedding Tasks** — Large-scale document imports run in a background thread without blocking the UI
- **Multi-user System** — User registration / login based on SQLAlchemy ORM + bcrypt; supports admin and regular user roles
- **Dual Database Engine** — Supports both SQLite (zero-config) and MySQL (production); switch via environment variable
- **Chat History Persistence** — All conversations are saved to the database and restored when revisiting the Q&A page
- **Knowledge Base Management** — Create / search / delete knowledge bases, upload files or batch-import from a directory, view file and vector statistics
- **Friendly Web UI** — Centered login card and sidebar navigation built with Streamlit

## Architecture

```
Mini-Rag/
├── app.py                          # Application entry point, page routing & session management
├── config.py                       # Global configuration (API, paths, database type, etc.)
├── .env                            # Environment variable file
│
├── docAnalysis/                    # Document loading module
│   ├── __init__.py
│   └── loader.py                   # DocumentLoader — multi-format document loader
│
├── docSplitter/                    # Document splitting module
│   ├── __init__.py
│   └── splitter.py                 # DocumentSplitter — text splitters
│
├── docEmbedding/                   # Document embedding & retrieval module
│   ├── __init__.py
│   ├── embedding.py                # EmbeddingManager — vector store, streaming retrieval, RAG chain
│   └── job_manager.py              # Background embedding job manager (thread + state persistence)
│
├── db/                             # Database module
│   ├── __init__.py
│   └── database.py                 # Database — SQLAlchemy ORM, supports SQLite & MySQL
│
├── ui/                             # Streamlit UI module
│   ├── __init__.py
│   ├── login.py                    # Centered login / register page
│   ├── knowledge_base.py           # Knowledge base management (search, delete confirm, background import)
│   ├── chat.py                     # WeChat-style streaming RAG Q&A page
│   └── user_manage.py              # User management (admin only)
│
└── data/                           # Runtime data directory (auto-created)
    ├── mini_rag.db                 # SQLite database file
    ├── chroma_db/                  # ChromaDB persistent vector store
    ├── embedding_jobs.json         # Background embedding job state persistence
    └── uploads/                    # Uploaded files storage
```

### Core Modules

| Module | Class / File | Responsibility |
|--------|--------------|----------------|
| `docAnalysis/loader.py` | `DocumentLoader` | Auto-selects a loader by file extension; supports single file and directory batch loading |
| `docSplitter/splitter.py` | `DocumentSplitter` | Provides `recursive` / `character` / `markdown_header` strategies |
| `docEmbedding/embedding.py` | `EmbeddingManager` | Manages OpenAI Embeddings + ChromaDB, streaming RAG retrieval, source extraction |
| `docEmbedding/job_manager.py` | `JobManager` | Singleton + daemon thread + state persistence; runs embedding jobs in background without blocking UI |
| `db/database.py` | `Database` | SQLAlchemy ORM, supports both SQLite and MySQL; manages users / knowledge bases / files / chat history |
| `ui/login.py` | `render_login_page` | Centered card-style login / register page |
| `ui/chat.py` | `render_chat_page` | WeChat-style chat bubbles + streaming generation + reference sources |
| `ui/knowledge_base.py` | `render_knowledge_base_page` | KB CRUD + background directory import + live job progress |
| `ui/user_manage.py` | `render_user_manage_page` | User search, delete, password change (admin only) |

### Database Schema

The persistence layer is built on **SQLAlchemy ORM**, which seamlessly switches between SQLite (default) and MySQL.

**users**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| username | VARCHAR(64) | Unique username |
| password_hash | VARCHAR(255) | bcrypt-hashed password |
| role | VARCHAR(20) | `admin` / `user` |
| created_at | DATETIME | Creation time |

**knowledge_bases**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| name | VARCHAR(128) | Knowledge base name |
| description | TEXT | Description |
| splitter_type | VARCHAR(32) | `recursive` / `character` / `markdown_header` |
| chunk_size | INTEGER | Chunk size |
| chunk_overlap | INTEGER | Chunk overlap |
| user_id | INTEGER | Owner user id |
| created_at | DATETIME | Creation time |

**kb_files**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| kb_id | INTEGER | Knowledge base id |
| file_name | VARCHAR(255) | File name |
| file_path | VARCHAR(512) | Stored file path |
| file_type | VARCHAR(32) | File type |
| chunk_count | INTEGER | Number of chunks after splitting |
| created_at | DATETIME | Creation time |

**chat_history**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| user_id | INTEGER | User id |
| kb_name | VARCHAR(255) | Knowledge base name |
| role | VARCHAR(50) | `user` / `assistant` |
| content | TEXT | Message content |
| sources | TEXT | JSON array of reference sources |
| created_at | DATETIME | Creation time |

## Usage

### Requirements

- Python 3.10+
- A virtual environment `.venv` (already configured)

### Launch

```bash
# Activate the virtual environment and start
.venv\Scripts\streamlit run app.py --server.headless true
```

Open `http://localhost:8501` in your browser.

### Default Admin Account

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |

> The admin account is created automatically on first launch. It is recommended to change the password immediately.

### Workflow

1. **Sign in** — Use the admin account on the centered login card, or switch to the `Register` tab to create a new user.
2. **Create a knowledge base** — Go to `Knowledge Base` → `Create`, fill in the name, description, and pick a splitter with parameters.
3. **Upload documents** — Go to `Knowledge Base` → `Upload` and select a target KB:
   - **Upload files**: pick local files directly; a live progress spinner is shown during processing.
   - **Specify a directory**: enter an absolute path on the server. After the system scans it, click `🚀 Start Embedding` to launch a background thread — **you can switch to other features while it runs**.
4. **Q&A** — Go to `RAG Q&A`; the most recent KB and its history are restored automatically:
   - AI replies are **streamed**, with the first token visible in 2–3 seconds.
   - WeChat-style layout: AI on the left (white bubble), user on the right (green bubble).
   - Message content is correctly rendered as Markdown (code blocks, lists, tables, etc.).
   - **Reference sources** (file + page) are shown directly under each answer.
5. **User management** (admin only) — Go to `User Management` to search / delete users and change passwords.

### Supported File Formats

| Extension | Type | Loader |
|-----------|------|--------|
| `.pdf` | PDF | PyPDFLoader |
| `.docx` / `.doc` | Word | Docx2txtLoader |
| `.pptx` / `.ppt` | PowerPoint | python-pptx |
| `.xlsx` / `.xls` | Excel | UnstructuredExcelLoader |
| `.csv` | CSV | CSVLoader |
| `.txt` | Plain text | TextLoader |
| `.md` / `.markdown` | Markdown | UnstructuredMarkdownLoader |

### Splitter Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Recursive character (recommended) | Splits hierarchically by separators; supports CJK punctuation | General documents |
| Character | Splits by line breaks | Simple plain text |
| Markdown header | Splits by `#` / `##` / `###` headers | Markdown documents |

## Configuration

### Environment Variables

Edit the `.env` file in the project root:

```env
# ========== LLM / Embedding ==========
# OpenAI API Key (required)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# OpenAI API base URL (compatible endpoints: Azure OpenAI, local deploy, domestic proxies, etc.)
OPENAI_API_BASE=https://api.openai.com/v1

# Chat model
LLM_MODEL=gpt-3.5-turbo

# Embedding model
EMBEDDING_MODEL=text-embedding-ada-002

# Embedding dimensions (optional, only text-embedding-3-* models support it; 0 = use model default)
EMBEDDING_DIMENSIONS=0

# ========== Database ==========
# Database type: sqlite (default, zero-config) / mysql (production)
DB_TYPE=sqlite

# MySQL settings (effective only when DB_TYPE=mysql)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=mini_rag
```

### Embedding Dimensions

`text-embedding-3-large` and `text-embedding-3-small` support custom output dimensions on compatible endpoints:

```env
EMBEDDING_DIMENSIONS=1024
```

| Value | Description |
|-------|-------------|
| `0` (default) | Use the model's native dimension (3-large: 3072, 3-small: 1536, ada-002: 1536) |
| Positive integer | Custom dimension; reduces storage and speeds up retrieval. Existing vectors must be re-imported. |

### Compatible Third-Party APIs

Any OpenAI-compatible service is supported — just change `OPENAI_API_BASE`:

```env
# Azure OpenAI
OPENAI_API_BASE=https://your-resource.openai.azure.com/openai/deployments/your-deployment

# Local deployment (Ollama, vLLM, etc.)
OPENAI_API_BASE=http://localhost:8000/v1

# Domestic proxy
OPENAI_API_BASE=https://your-proxy.com/v1
```

The system automatically appends `/v1` if missing.

### Database Switch

Switch between SQLite and MySQL via `DB_TYPE`:

```env
# SQLite (default, no extra config)
DB_TYPE=sqlite

# MySQL
DB_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=mini_rag
```

> Create the target database with charset `utf8mb4` in advance; tables are created automatically.

### Data Paths

Data paths are defined in `config.py` and live under `data/` by default:

| Config | Default Path | Description |
|--------|--------------|-------------|
| `DB_PATH` | `data/mini_rag.db` | SQLite database file |
| `CHROMA_PERSIST_DIR` | `data/chroma_db/` | ChromaDB vector store |
| `UPLOAD_DIR` | `data/uploads/` | Uploaded files |

## Maintenance

### Dependencies

```bash
# Install dependencies
.venv\Scripts\pip install -r requirements.txt
```

Key packages:

| Package | Purpose |
|---------|---------|
| `langchain` | LangChain core framework |
| `langchain-openai` | OpenAI integration |
| `langchain-chroma` | ChromaDB integration |
| `langchain-community` | Community document loaders |
| `langchain-core` | Core abstractions (Document, PromptTemplate, etc.) |
| `chromadb` | ChromaDB vector database |
| `streamlit` | Web UI framework |
| `sqlalchemy` | ORM abstraction, supports SQLite & MySQL |
| `pymysql` | MySQL driver (only when DB_TYPE=mysql) |
| `python-docx` | Word parsing |
| `python-pptx` | PPT parsing |
| `openpyxl` | Excel parsing |
| `pypdf` | PDF parsing |
| `bcrypt` | Password hashing |
| `python-dotenv` | Environment variable loader |

### Backup

```bash
# Backup SQLite database
copy data\mini_rag.db data\mini_rag.db.bak

# Backup ChromaDB
xcopy /E /I data\chroma_db data\chroma_db_bak
```

> For MySQL, use `mysqldump` against the target database.

### Data Cleanup

- **Delete a knowledge base**: Click `🗑️` in the knowledge base page and confirm. The system removes the ChromaDB collection, related file records, and chat history.
- **Reset database**: Delete `data/mini_rag.db` and restart. All users, knowledge bases, and chat history will be lost.
- **Clear vector data**: Delete `data/chroma_db/`. Knowledge bases must be re-uploaded.
- **Clear background jobs**: Delete `data/embedding_jobs.json`.

### FAQ

**Q: The page is blank or errors out on launch.**

Check that `OPENAI_API_KEY` in `.env` is set and `OPENAI_API_BASE` is reachable.

**Q: Vector count stays at 0 after upload.**

Confirm the file format is supported, and that the file is not empty or unparseable. Check terminal logs for details.

**Q: AI replies are very slow.**

Streaming output shows the first token in 2–3 seconds. If the overall generation is slow, try:
- Lowering `top_k` in the sidebar (Retrieval Count)
- Reducing `EMBEDDING_DIMENSIONS` in `.env`
- Switching to a lighter `LLM_MODEL`

**Q: Chat content shows raw source like `</div>`.**

This issue has been fixed: AI replies now use `st.chat_message` natively and Markdown is rendered via `st.markdown`.

**Q: A background embedding job is stuck on a file.**

The file may be corrupted or oversized. Remove it manually and re-upload.

**Q: How to change the default port?**

```bash
.venv\Scripts\streamlit run app.py --server.port 8502 --server.headless true
```

**Q: Switching to MySQL fails on launch.**

Make sure `pymysql` is installed (`pip install pymysql`) and the `mini_rag` database (charset `utf8mb4`) exists in MySQL.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | LangChain 1.x |
| LLM | OpenAI GPT (compatible endpoints, streaming supported) |
| Embedding | OpenAI Embeddings (custom dimensions supported) |
| Vector Database | ChromaDB |
| Relational Database | SQLite / MySQL (SQLAlchemy ORM abstraction) |
| Password Hashing | bcrypt |
| Web UI | Streamlit |
| Document Parsing | PyPDF / python-docx / python-pptx / openpyxl / Unstructured |
| Concurrency | threading daemon threads + JSON state persistence |
