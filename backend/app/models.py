"""Pydantic and SQLModel data models for InfraAI"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField, Column, JSON


# ========== API Models (Pydantic) ==========

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # "user" or "ai"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request payload"""
    session_id: str
    prompt: str
    chatMode: Optional[str] = "chat"
    useRAG: Optional[bool] = False
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Chat response payload"""
    session_id: str
    message: ChatMessage
    selfHealingEnabled: bool = False
    ragApplied: bool = False


class Policy(BaseModel):
    """Policy model for API responses"""
    id: Optional[int] = None
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int = Field(default=100, ge=0)
    created_at: Optional[datetime] = None


class PolicyCreate(BaseModel):
    """Policy creation payload"""
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int = Field(default=100, ge=0)


class PrometheusAlert(BaseModel):
    """Prometheus webhook alert payload"""
    version: Optional[str] = "4"
    groupKey: Optional[str] = None
    status: str  # "firing" or "resolved"
    receiver: Optional[str] = None
    groupLabels: Dict[str, Any] = {}
    commonLabels: Dict[str, Any] = {}
    commonAnnotations: Dict[str, Any] = {}
    externalURL: Optional[str] = None
    alerts: List[Dict[str, Any]] = []


class SystemAsset(BaseModel):
    """System asset model"""
    id: Optional[int] = None
    ip: str
    hostname: Optional[str] = None
    type: str  # "vm", "pod", "server"
    services: List[str] = []
    last_seen: Optional[datetime] = None


class DiscoverRequest(BaseModel):
    """Network discovery request"""
    subnet: str = "192.168.1.0/24"


# ========== Database Models (SQLModel) ==========

class PolicyDB(SQLModel, table=True):
    """Policy database table"""
    __tablename__ = "policies"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(index=True)
    condition: Dict[str, Any] = SQLField(sa_column=Column(JSON))
    action: Dict[str, Any] = SQLField(sa_column=Column(JSON))
    priority: int = SQLField(default=100, index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class SystemAssetDB(SQLModel, table=True):
    """System asset database table"""
    __tablename__ = "system_assets"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    ip: str = SQLField(unique=True, index=True)
    hostname: Optional[str] = None
    type: str = SQLField(index=True)  # "vm", "pod", "server"
    services: List[str] = SQLField(default=[], sa_column=Column(JSON))
    last_seen: datetime = SQLField(default_factory=datetime.utcnow)


class ChatHistoryDB(SQLModel, table=True):
    """Chat history database table"""
    __tablename__ = "chat_history"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    session_id: str = SQLField(index=True)
    role: str
    content: str
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)


class JobLogDB(SQLModel, table=True):
    """Job execution log table"""
    __tablename__ = "job_logs"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    action: str
    target: str
    status: str
    result: Optional[str] = None
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
