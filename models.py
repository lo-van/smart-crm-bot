from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    remind_interval_days = Column(Integer, default=3)          # раз в сколько дней напоминать
    reminders_enabled = Column(Boolean, default=True)          # включены ли напоминания
    last_remind_check_at = Column(DateTime, nullable=True)     # когда последний раз проверяли
    contacts = relationship("Contact", back_populates="owner", lazy="dynamic")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    telegram_user_id = Column(BigInteger, nullable=True, unique=True)
    name = Column(String, nullable=False)
    sphere = Column(String, nullable=True)
    tags = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    telegram_handle = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    last_contacted_at = Column(DateTime, default=datetime.datetime.utcnow)
    remind_interval_days = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    remind_disabled = Column(Boolean, default=False)
    owner = relationship("User", back_populates="contacts")
    messages = relationship("Message", back_populates="contact", lazy="dynamic")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    telegram_message_id = Column(BigInteger, nullable=True)
    text = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    from_me = Column(Boolean, default=False)
    media_type = Column(String, nullable=True)
    contact = relationship("Contact", back_populates="messages")
