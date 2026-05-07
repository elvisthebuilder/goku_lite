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
        
        self.engine = create_engine(
            self.url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"sslmode": "require"} if "sqlite" not in self.url else {}
        )
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

    def get_messages(self, session_id: str, limit: int = 50):
        with self.Session() as db:
            messages = db.query(MessageModel).filter_by(session_id=session_id).order_by(MessageModel.created_at).all()
            return [{"role": m.role, "content": m.content} for m in messages]

    def compact_history(self, session_id: str, summary: str, keep_count: int = 5):
        """
        Implements history compaction.
        Keeps the latest 'keep_count' messages and replaces the rest with a summary.
        """
        with self.Session() as db:
            messages = db.query(MessageModel).filter_by(session_id=session_id).order_by(MessageModel.created_at).all()
            if len(messages) <= keep_count:
                return

            # Messages to delete (everything except the last 'keep_count')
            to_delete = messages[:-keep_count]
            for m in to_delete:
                db.delete(m)
            
            # Insert the summary as a system message at the start
            summary_msg = MessageModel(
                session_id=session_id, 
                role="system", 
                content=f"[CONVERSATION SUMMARY]: {summary}",
                msg_type="summary"
            )
            db.add(summary_msg)
            db.commit()
            logger.info(f"Compacted history for session {session_id}. Kept last {keep_count} turns.")

    def clear_history(self, session_id: str):
        """Wipes all messages for a specific session."""
        with self.Session() as db:
            db.query(MessageModel).filter_by(session_id=session_id).delete()
            db.commit()

    def delete_session(self, session_id: str):
        """Deletes the entire session and its messages."""
        with self.Session() as db:
            session = db.query(SessionModel).filter_by(id=session_id).first()
            if session:
                db.delete(session)
                db.commit()

    def wipe_all_data(self):
        """DANGER: Wipes every single session and message in the entire database."""
        with self.Session() as db:
            # Drop all tables and recreate them to ensure a clean slate
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            logger.info("SQL Database wiped clean (all sessions deleted).")

history = CloudHistory()
