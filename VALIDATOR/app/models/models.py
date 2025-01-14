from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    uuid = Column(String, primary_key=True, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    matricula = Column(String, nullable=True, unique=True)
    codigo_aasp = Column(String, nullable=True, unique=True)
    access_token = Column(String, nullable=False)
    tipo = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notion_databases = relationship("NotionDatabase", back_populates="user")

class NotionDatabase(Base):
    __tablename__ = "notion_databases"

    uuid = Column(String, ForeignKey("users.uuid"), primary_key=True, nullable=False)
    notion_database_id = Column(String, unique=True, nullable=False)
    matricula_db_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notion_databases")
