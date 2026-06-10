from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, func
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    condition = Column(String(50), nullable=True)
    availability = Column(String(50), nullable=True)
    brand = Column(String(100), nullable=True)
    price_str = Column(String(50), nullable=True)
    price = Column(Numeric(10, 2), nullable=True, index=True)  # Numeric price for filtering
    link = Column(String(512), nullable=True)
    image_link = Column(String(512), nullable=True)
    category = Column(String(255), nullable=True, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
