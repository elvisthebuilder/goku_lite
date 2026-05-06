import logging
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey
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
    role = Column(String) # user, agent, system
    content = Column(Text)
    msg_type = Column(String, default='message')
    metadata_json = Column(Text) # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("SessionModel", back_populates="messages")

class CloudHistory:
    def __init__(self):
        self.url = config.DATABASE_URL
        if not self.url:
            self.url = "sqlite:///goku_lite_fallback.db"
            logger.warning("DATABASE_URL not set. Falling back to local SQLite.")
        
        self.engine = create_engine(self.url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_message(self, session_id: str, role: str, content: str, msg_type: str = 'message'):
        with self.Session() as db:
            # Ensure session exists
            session = db.query(SessionModel).filter_by(id=session_id).first()
            if not session:
                session = SessionModel(id=session_id, title=content[:30] + "..." if len(content) > 30 else content)
                db.add(session)
            
            msg = MessageModel(session_id=session_id, role=role, content=content, msg_type=msg_type)
            db.add(msg)
            db.commit()

    def get_messages(self, session_id: str):
        with self.Session() as db:
            messages = db.query(MessageModel).filter_by(session_id=session_id).order_by(MessageModel.created_at).all()
            return [{"role": m.role, "content": m.content} for m in messages]

history = CloudHistory()
