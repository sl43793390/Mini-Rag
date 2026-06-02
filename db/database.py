import os
import bcrypt
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
    Session,
)

from config import DB_TYPE, DB_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    knowledge_bases = relationship("KnowledgeBase", back_populates="user")
    chat_histories = relationship("ChatHistory", back_populates="user")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default="")
    splitter_type = Column(String(50), nullable=False, default="recursive")
    chunk_size = Column(Integer, nullable=False, default=500)
    chunk_overlap = Column(Integer, nullable=False, default=50)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="knowledge_bases")
    files = relationship("KbFile", back_populates="knowledge_base", cascade="all, delete-orphan")


class KbFile(Base):
    __tablename__ = "kb_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    knowledge_base = relationship("KnowledgeBase", back_populates="files")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kb_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="chat_histories")


def _build_database_url() -> str:
    if DB_TYPE == "mysql":
        return (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
        )
    else:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return f"sqlite:///{DB_PATH}"


class Database:
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = _build_database_url()
        self.engine = create_engine(database_url, echo=False, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._init_db()

    def _init_db(self):
        Base.metadata.create_all(self.engine)
        self._ensure_default_admin()

    def _ensure_default_admin(self):
        session = self.SessionLocal()
        try:
            existing = session.query(User).filter_by(username="admin").first()
            if not existing:
                password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                admin = User(
                    username="admin",
                    password_hash=password_hash,
                    role="admin",
                    created_at=datetime.now(),
                )
                session.add(admin)
                session.commit()
        finally:
            session.close()

    def _get_session(self) -> Session:
        return self.SessionLocal()

    # ── User CRUD ──

    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        session = self._get_session()
        try:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                created_at=datetime.now(),
            )
            session.add(user)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        session = self._get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user is None:
                return None
            if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else "",
                }
            return None
        finally:
            session.close()

    def get_user(self, username: str) -> Optional[Dict]:
        session = self._get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user is None:
                return None
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else "",
            }
        finally:
            session.close()

    def get_all_users(self) -> List[Dict]:
        session = self._get_session()
        try:
            users = session.query(User).all()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "created_at": u.created_at.isoformat() if u.created_at else "",
                }
                for u in users
            ]
        finally:
            session.close()

    def delete_user(self, user_id: int) -> bool:
        session = self._get_session()
        try:
            result = session.query(User).filter(User.id == user_id, User.role != "admin").delete()
            session.commit()
            return result > 0
        finally:
            session.close()

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        session = self._get_session()
        try:
            password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            result = session.query(User).filter(User.id == user_id).update({"password_hash": password_hash})
            session.commit()
            return result > 0
        finally:
            session.close()

    # ── KnowledgeBase CRUD ──

    def create_knowledge_base(
        self,
        name: str,
        user_id: int,
        description: str = "",
        splitter_type: str = "recursive",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> Optional[int]:
        session = self._get_session()
        try:
            kb = KnowledgeBase(
                name=name,
                description=description,
                splitter_type=splitter_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                user_id=user_id,
                created_at=datetime.now(),
            )
            session.add(kb)
            session.commit()
            return kb.id
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def get_knowledge_bases(self, user_id: Optional[int] = None) -> List[Dict]:
        session = self._get_session()
        try:
            query = session.query(KnowledgeBase)
            if user_id:
                query = query.filter(KnowledgeBase.user_id == user_id)
            kbs = query.order_by(KnowledgeBase.created_at.desc()).all()
            return [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description or "",
                    "splitter_type": kb.splitter_type,
                    "chunk_size": kb.chunk_size,
                    "chunk_overlap": kb.chunk_overlap,
                    "user_id": kb.user_id,
                    "created_at": kb.created_at.isoformat() if kb.created_at else "",
                }
                for kb in kbs
            ]
        finally:
            session.close()

    def get_knowledge_base(self, kb_id: int) -> Optional[Dict]:
        session = self._get_session()
        try:
            kb = session.query(KnowledgeBase).filter_by(id=kb_id).first()
            if kb is None:
                return None
            return {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description or "",
                "splitter_type": kb.splitter_type,
                "chunk_size": kb.chunk_size,
                "chunk_overlap": kb.chunk_overlap,
                "user_id": kb.user_id,
                "created_at": kb.created_at.isoformat() if kb.created_at else "",
            }
        finally:
            session.close()

    def get_knowledge_base_by_name(self, name: str) -> Optional[Dict]:
        session = self._get_session()
        try:
            kb = session.query(KnowledgeBase).filter_by(name=name).first()
            if kb is None:
                return None
            return {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description or "",
                "splitter_type": kb.splitter_type,
                "chunk_size": kb.chunk_size,
                "chunk_overlap": kb.chunk_overlap,
                "user_id": kb.user_id,
                "created_at": kb.created_at.isoformat() if kb.created_at else "",
            }
        finally:
            session.close()

    def delete_knowledge_base(self, kb_id: int) -> bool:
        session = self._get_session()
        try:
            session.query(KbFile).filter(KbFile.kb_id == kb_id).delete()
            result = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).delete()
            session.commit()
            return result > 0
        finally:
            session.close()

    # ── KbFile CRUD ──

    def add_file_to_kb(
        self,
        kb_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        chunk_count: int = 0,
    ) -> Optional[int]:
        session = self._get_session()
        try:
            kb_file = KbFile(
                kb_id=kb_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                chunk_count=chunk_count,
                created_at=datetime.now(),
            )
            session.add(kb_file)
            session.commit()
            return kb_file.id
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def get_kb_files(self, kb_id: int) -> List[Dict]:
        session = self._get_session()
        try:
            files = session.query(KbFile).filter_by(kb_id=kb_id).all()
            return [
                {
                    "id": f.id,
                    "kb_id": f.kb_id,
                    "file_name": f.file_name,
                    "file_path": f.file_path,
                    "file_type": f.file_type,
                    "chunk_count": f.chunk_count,
                    "created_at": f.created_at.isoformat() if f.created_at else "",
                }
                for f in files
            ]
        finally:
            session.close()

    def get_kb_file_count(self, kb_id: int) -> int:
        session = self._get_session()
        try:
            return session.query(KbFile).filter_by(kb_id=kb_id).count()
        finally:
            session.close()

    def update_file_chunk_count(self, file_id: int, chunk_count: int):
        session = self._get_session()
        try:
            session.query(KbFile).filter(KbFile.id == file_id).update({"chunk_count": chunk_count})
            session.commit()
        finally:
            session.close()

    # ── ChatHistory CRUD ──

    def add_chat_message(
        self,
        user_id: int,
        kb_name: str,
        role: str,
        content: str,
        sources: str = "",
    ) -> Optional[int]:
        session = self._get_session()
        try:
            msg = ChatHistory(
                user_id=user_id,
                kb_name=kb_name,
                role=role,
                content=content,
                sources=sources,
                created_at=datetime.now(),
            )
            session.add(msg)
            session.commit()
            return msg.id
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def get_chat_history(
        self,
        user_id: int,
        kb_name: str,
        limit: int = 50,
    ) -> List[Dict]:
        session = self._get_session()
        try:
            messages = (
                session.query(ChatHistory)
                .filter_by(user_id=user_id, kb_name=kb_name)
                .order_by(ChatHistory.created_at.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "kb_name": m.kb_name,
                    "role": m.role,
                    "content": m.content,
                    "sources": m.sources or "",
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in messages
            ]
        finally:
            session.close()

    def get_last_kb_name(self, user_id: int) -> Optional[str]:
        session = self._get_session()
        try:
            last_msg = (
                session.query(ChatHistory)
                .filter_by(user_id=user_id)
                .order_by(ChatHistory.created_at.desc())
                .first()
            )
            return last_msg.kb_name if last_msg else None
        finally:
            session.close()

    def clear_chat_history(self, user_id: int, kb_name: str) -> bool:
        session = self._get_session()
        try:
            session.query(ChatHistory).filter_by(user_id=user_id, kb_name=kb_name).delete()
            session.commit()
            return True
        finally:
            session.close()
