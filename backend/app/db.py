"""Database connection and CRUD operations"""

import os
from typing import List, Optional
from datetime import datetime
from sqlmodel import SQLModel, create_engine, select, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager

from app.models import (
    PolicyDB, SystemAssetDB, ChatHistoryDB, JobLogDB,
    Policy, SystemAsset, ChatMessage
)


# Database configuration
DATABASE_URL = os.getenv("POSTGRES_DSN", "postgresql+asyncpg://infraal:infraal@localhost/infraal")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session():
    """Get async database session"""
    async with async_session_maker() as session:
        yield session


# ========== Policy CRUD ==========

async def create_policy(name: str, condition: dict, action: dict, priority: int = 100) -> Policy:
    """Create a new policy"""
    async with get_session() as session:
        policy_db = PolicyDB(
            name=name,
            condition=condition,
            action=action,
            priority=priority
        )
        session.add(policy_db)
        await session.commit()
        await session.refresh(policy_db)
        return Policy(
            id=policy_db.id,
            name=policy_db.name,
            condition=policy_db.condition,
            action=policy_db.action,
            priority=policy_db.priority,
            created_at=policy_db.created_at
        )


async def get_policy(policy_id: int) -> Optional[Policy]:
    """Get a policy by ID"""
    async with get_session() as session:
        result = await session.execute(select(PolicyDB).where(PolicyDB.id == policy_id))
        policy_db = result.scalar_one_or_none()
        if policy_db:
            return Policy(
                id=policy_db.id,
                name=policy_db.name,
                condition=policy_db.condition,
                action=policy_db.action,
                priority=policy_db.priority,
                created_at=policy_db.created_at
            )
        return None


async def get_all_policies() -> List[Policy]:
    """Get all policies, sorted by priority"""
    async with get_session() as session:
        result = await session.execute(
            select(PolicyDB).order_by(PolicyDB.priority.asc())
        )
        policies_db = result.scalars().all()
        return [
            Policy(
                id=p.id,
                name=p.name,
                condition=p.condition,
                action=p.action,
                priority=p.priority,
                created_at=p.created_at
            )
            for p in policies_db
        ]


async def delete_policy(policy_id: int) -> bool:
    """Delete a policy by ID"""
    async with get_session() as session:
        result = await session.execute(select(PolicyDB).where(PolicyDB.id == policy_id))
        policy_db = result.scalar_one_or_none()
        if policy_db:
            await session.delete(policy_db)
            await session.commit()
            return True
        return False


# ========== System Asset CRUD ==========

async def upsert_asset(ip: str, hostname: Optional[str], asset_type: str, services: List[str]) -> SystemAsset:
    """Insert or update a system asset"""
    async with get_session() as session:
        result = await session.execute(select(SystemAssetDB).where(SystemAssetDB.ip == ip))
        asset_db = result.scalar_one_or_none()
        
        if asset_db:
            # Update existing
            asset_db.hostname = hostname or asset_db.hostname
            asset_db.type = asset_type
            asset_db.services = services
            asset_db.last_seen = datetime.utcnow()
        else:
            # Create new
            asset_db = SystemAssetDB(
                ip=ip,
                hostname=hostname,
                type=asset_type,
                services=services
            )
            session.add(asset_db)
        
        await session.commit()
        await session.refresh(asset_db)
        return SystemAsset(
            id=asset_db.id,
            ip=asset_db.ip,
            hostname=asset_db.hostname,
            type=asset_db.type,
            services=asset_db.services,
            last_seen=asset_db.last_seen
        )


async def get_all_assets() -> List[SystemAsset]:
    """Get all system assets"""
    async with get_session() as session:
        result = await session.execute(select(SystemAssetDB))
        assets_db = result.scalars().all()
        return [
            SystemAsset(
                id=a.id,
                ip=a.ip,
                hostname=a.hostname,
                type=a.type,
                services=a.services,
                last_seen=a.last_seen
            )
            for a in assets_db
        ]


# ========== Chat History CRUD ==========

async def add_chat_message(session_id: str, role: str, content: str) -> ChatMessage:
    """Add a chat message to history"""
    async with get_session() as session:
        chat_db = ChatHistoryDB(
            session_id=session_id,
            role=role,
            content=content
        )
        session.add(chat_db)
        await session.commit()
        await session.refresh(chat_db)
        return ChatMessage(
            role=chat_db.role,
            content=chat_db.content,
            timestamp=chat_db.timestamp
        )


async def get_chat_history(session_id: str, limit: int = 50) -> List[ChatMessage]:
    """Get chat history for a session"""
    async with get_session() as session:
        result = await session.execute(
            select(ChatHistoryDB)
            .where(ChatHistoryDB.session_id == session_id)
            .order_by(ChatHistoryDB.timestamp.asc())
            .limit(limit)
        )
        messages_db = result.scalars().all()
        return [
            ChatMessage(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp
            )
            for m in messages_db
        ]


# ========== Job Log CRUD ==========

async def log_job(action: str, target: str, status: str, result: Optional[str] = None):
    """Log a job execution"""
    async with get_session() as session:
        job_db = JobLogDB(
            action=action,
            target=target,
            status=status,
            result=result
        )
        session.add(job_db)
        await session.commit()
