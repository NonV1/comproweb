# app/models.py
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Boolean, ForeignKey, BigInteger,
    TIMESTAMP, Enum as SAEnum, text
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base  # ต้องมี Base จาก sessionmaker/engine ของโปรเจกต์คุณ

# ---------- Python Enums (ผูกกับ enum ใน DB เดิม) ----------
class UserRole(enum.Enum):
    user = "user"
    admin = "admin"

class TicketStatus(enum.Enum):
    open               = "open"
    awaiting_payment   = "awaiting_payment"
    payment_held       = "payment_held"
    awaiting_delivery  = "awaiting_delivery"
    in_review          = "in_review"
    completed          = "completed"
    cancelled          = "cancelled"
    disputed           = "disputed"
    refunded           = "refunded"

class PaymentStatus(enum.Enum):
    pending  = "pending"
    held     = "held"
    released = "released"
    refunded = "refunded"
    failed   = "failed"

# ---------- Tables ----------
class Users(Base):
    __tablename__ = "users"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, nullable=False, unique=True)
    username      = Column(String, nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(SAEnum(UserRole, name="user_role"), nullable=False, server_default=text("'user'::user_role"))
    is_active     = Column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    # relationships (ใช้ชื่อคลาสที่อยู่ด้านล่าง)
    opened_tickets = relationship("Tickets", foreign_keys="Tickets.opener_id")
    buy_tickets    = relationship("Tickets", foreign_keys="Tickets.buyer_id")
    sell_tickets   = relationship("Tickets", foreign_keys="Tickets.seller_id")


class Tickets(Base):
    __tablename__ = "tickets"

    id          = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title       = Column(Text, nullable=False)
    description = Column(Text)
    opener_id   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    buyer_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    seller_id   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    admin_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status      = Column(SAEnum(TicketStatus, name="ticket_status"), nullable=False, server_default=text("'open'::ticket_status"))
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    closed_at   = Column(TIMESTAMP(timezone=True), nullable=True)

    # relationships
    opener   = relationship("Users", foreign_keys=[opener_id])
    buyer    = relationship("Users", foreign_keys=[buyer_id])
    seller   = relationship("Users", foreign_keys=[seller_id])
    admin    = relationship("Users", foreign_keys=[admin_id])

    messages = relationship("TicketMessages", back_populates="ticket", cascade="all, delete-orphan")
    payments = relationship("EscrowPayments",  back_populates="ticket", cascade="all, delete-orphan")
    logs     = relationship("ActivityLogs",    back_populates="ticket", cascade="all, delete-orphan")


class TicketMessages(Base):
    __tablename__ = "ticket_messages"

    id          = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id   = Column(PG_UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    sender_id   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),   nullable=False)
    body        = Column(Text, nullable=False)
    attachments = Column(JSONB)  # list/obj
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    # relationships
    ticket = relationship("Tickets", back_populates="messages")
    sender = relationship("Users")


class EscrowPayments(Base):
    __tablename__ = "escrow_payments"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id    = Column(PG_UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    payer_id     = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),   nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    currency     = Column(String(3), nullable=False, server_default=text("'THB'"))
    status       = Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False, server_default=text("'pending'::payment_status"))
    provider     = Column(Text)
    provider_ref = Column(Text)
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    released_at  = Column(TIMESTAMP(timezone=True))
    refunded_at  = Column(TIMESTAMP(timezone=True))

    # relationships
    ticket = relationship("Tickets", back_populates="payments")
    payer  = relationship("Users")


class ActivityLogs(Base):
    __tablename__ = "activity_logs"

    id        = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id  = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),   nullable=True)
    ticket_id = Column(PG_UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    action    = Column(Text, nullable=False)
    meta      = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    # relationships
    actor  = relationship("Users")
    ticket = relationship("Tickets", back_populates="logs")


# Backwards-compatible aliases: some modules import `User`/`Ticket` singular.
# The declarative classes in this file are named `Users`/`Tickets`, but other
# parts of the codebase expect `User`/`Ticket`. Provide aliases to avoid
# ImportError without changing many files.
User = Users
Ticket = Tickets
