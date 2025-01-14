from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.db_config import Base

class User(Base):
    __tablename__ = "users"

    uuid = Column(String, primary_key=True, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    matricula = Column(String, nullable=True, unique=True)
    codigo_aasp = Column(String, nullable=True, unique=True)
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
    notion_matricula_id = Column(String, unique=True, nullable=False)    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User", 
        back_populates="notion_databases", 
        lazy="selectin"
    )