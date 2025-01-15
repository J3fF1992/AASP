from sqlalchemy import Column, String, ForeignKey, DateTime,UniqueConstraint,Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.db_config import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class User(Base):
    __tablename__ = "users"

    uuid = Column(String, primary_key=True, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    matricula = Column(String, nullable=True, unique=True)
    codigo_aasp = Column(String, nullable=True, unique=True)
    tipo = Column(String, nullable=True, unique=True)
    access_token = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notion_databases = relationship(
        "NotionDatabase", 
        back_populates="user", 
        lazy="selectin"
    )

class NotionDatabase(Base):
    __tablename__ = "notion_databases"

    uuid = Column(String, ForeignKey("users.uuid"), primary_key=True, nullable=False)
    notion_database_id = Column(String, unique=True, nullable=False)
    matricula_db_id = Column(String, unique=True, nullable=False)    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User", 
        back_populates="notion_databases", 
        lazy="selectin"
    )


class UltimaIntimacaoProcessada(Base):
    __tablename__ = 'ultima_intimacao_processada'

    usuario_uuid = Column(String, primary_key=True, index=True)
    ultima_data_processada = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("usuario_uuid", name="uq_usuario_uuid"),
    )