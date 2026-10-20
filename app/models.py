"""Portable relational schema. All business queries must include tenant_id."""
import time
import uuid
from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, Index, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = 'tenants'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[int] = mapped_column(Integer, index=True)


class Dispute(Base):
    __tablename__ = 'disputes'
    __table_args__ = (UniqueConstraint('tenant_id', 'paypal_id'), Index('ix_queue', 'tenant_id', 'status', 'due_at', 'id'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'))
    paypal_id: Mapped[str] = mapped_column(String(255))
    customer: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(100))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    status: Mapped[str] = mapped_column(String(24), default='OPEN')
    due_at: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
    draft: Mapped[str] = mapped_column(Text, default='')
    draft_source: Mapped[str] = mapped_column(String(32), default='')
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider_updated: Mapped[str] = mapped_column(String(64), default='')


class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    dispute_id: Mapped[str] = mapped_column(ForeignKey('disputes.id'), index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))


class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()), index=True)


class Webhook(Base):
    __tablename__ = 'webhook_inbox'
    __table_args__ = (UniqueConstraint('tenant_id', 'event_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'))
    event_id: Mapped[str] = mapped_column(String(255))
    payload: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(24), default='PENDING', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[int] = mapped_column(Integer, default=0, index=True)


class Submission(Base):
    __tablename__ = 'submissions'
    __table_args__ = (UniqueConstraint('tenant_id', 'request_key'), UniqueConstraint('dispute_id', 'draft_version'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'))
    dispute_id: Mapped[str] = mapped_column(ForeignKey('disputes.id'), index=True)
    request_key: Mapped[str] = mapped_column(String(128))
    draft_version: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), default='PENDING')
    provider_reference: Mapped[str] = mapped_column(String(255), default='')


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    expires: Mapped[int] = mapped_column(Integer, index=True)


def database(url):
    engine = create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread': False, 'timeout': 20} if url.startswith('sqlite') else {})
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_config(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA journal_mode=WAL')
    return engine, sessionmaker(engine, expire_on_commit=False)

