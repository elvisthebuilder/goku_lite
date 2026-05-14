import logging
import json
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from .config import config

logger = logging.getLogger(__name__)
Base = declarative_base()

class SessionModel(Base):
    __tablename__ = 'sessions'
    id = Column(String, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")

class MessageModel(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.id'))
    role = Column(String) 
    content = Column(Text)
    msg_type = Column(String, default='message')
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("SessionModel", back_populates="messages")

class TaskModel(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SettingModel(Base):
    __tablename__ = 'settings'
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CloudHistory:
    def __init__(self):
        self.url = config.DATABASE_URL
        if not self.url:
            self.url = "sqlite:///goku_lite_fallback.db"
            logger.warning("DATABASE_URL not set. Falling back to local SQLite.")
        
        self.engine = create_engine(
            self.url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"sslmode": "require"} if "sqlite" not in self.url else {}
        )
        
        import time
        for attempt in range(1, 4):
            try:
                Base.metadata.create_all(self.engine)
                break
            except Exception as e:
                if attempt == 3: raise
                time.sleep(attempt * 2)
                
        self.Session = sessionmaker(bind=self.engine)

    # --- Message Management ---
    def add_message(self, session_id: str, role: str, content: str, msg_type: str = 'message'):
        with self.Session() as db:
            session = db.query(SessionModel).filter_by(id=session_id).first()
            if not session:
                session = SessionModel(id=session_id, title=content[:30] + "..." if len(content) > 30 else content)
                db.add(session)
            msg = MessageModel(session_id=session_id, role=role, content=content, msg_type=msg_type)
            db.add(msg)
            db.commit()

    def get_messages(self, session_id: str, limit: int = 50):
        with self.Session() as db:
            messages = db.query(MessageModel).filter_by(session_id=session_id).order_by(MessageModel.created_at).all()
            return [{"role": m.role, "content": m.content} for m in messages]

    # --- Task Management (Cloud Native) ---
    def add_task(self, description: str):
        with self.Session() as db:
            task = TaskModel(description=description)
            db.add(task)
            db.commit()

    def get_tasks(self):
        with self.Session() as db:
            return db.query(TaskModel).all()

    def clear_tasks(self):
        with self.Session() as db:
            db.query(TaskModel).delete()
            db.commit()

    # --- Settings Management (Cloud Native) ---
    def set_setting(self, key: str, value: str):
        with self.Session() as db:
            setting = db.query(SettingModel).filter_by(key=key).first()
            if setting: setting.value = value
            else: db.add(SettingModel(key=key, value=value))
            db.commit()

    def get_setting(self, key: str, default=None):
        with self.Session() as db:
            setting = db.query(SettingModel).filter_by(key=key).first()
            return setting.value if setting else default

    def clear_history(self, session_id: str):
        with self.Session() as db:
            db.query(MessageModel).filter_by(session_id=session_id).delete()
            db.commit()

    def wipe_all_data(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

history = CloudHistory()
