-- ==========================================================
-- Mini-Rag MySQL 数据库初始化脚本
-- ==========================================================
-- 使用方法（在 MySQL 客户端或命令行中执行）：
--   mysql -u root -p < init_mysql.sql
-- 或者先登录再执行：
--   source /path/to/init_mysql.sql
-- ==========================================================

-- 1. 创建数据库（字符集 utf8mb4 以支持 emoji 与多语言）
DROP DATABASE IF EXISTS mini_rag;
CREATE DATABASE mini_rag
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE mini_rag;

-- ==========================================================
-- 2. 用户表
-- ==========================================================
CREATE TABLE users (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    username        VARCHAR(64)     NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    role            VARCHAR(20)     NOT NULL DEFAULT 'user',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户表';

-- ==========================================================
-- 3. 知识库表
-- ==========================================================
CREATE TABLE knowledge_bases (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    name            VARCHAR(128)    NOT NULL,
    description     TEXT            NULL,
    splitter_type   VARCHAR(32)     NOT NULL DEFAULT 'recursive',
    chunk_size      INT             NOT NULL DEFAULT 500,
    chunk_overlap   INT             NOT NULL DEFAULT 50,
    user_id         BIGINT          NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_kb_name (name),
    KEY idx_kb_user_id (user_id),
    CONSTRAINT fk_kb_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='知识库表';

-- ==========================================================
-- 4. 知识库文件表
-- ==========================================================
CREATE TABLE kb_files (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    kb_id           BIGINT          NOT NULL,
    file_name       VARCHAR(255)    NOT NULL,
    file_path       VARCHAR(512)    NOT NULL,
    file_type       VARCHAR(32)     NOT NULL,
    chunk_count     INT             NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_kb_files_kb_id (kb_id),
    CONSTRAINT fk_kb_files_kb FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='知识库文件表';

-- ==========================================================
-- 5. 聊天历史表
-- ==========================================================
CREATE TABLE chat_history (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    user_id         BIGINT          NOT NULL,
    kb_name         VARCHAR(255)    NOT NULL,
    role            VARCHAR(50)     NOT NULL,
    content         TEXT            NOT NULL,
    sources         TEXT            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_chat_user_kb (user_id, kb_name, created_at),
    CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='聊天历史表';

-- ==========================================================
-- 6. 验证
-- ==========================================================
SHOW TABLES;
SELECT 'Mini-Rag MySQL database initialized successfully.' AS status;
