from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import (
    Column, Enum as PgEnum, Text, String, Boolean, BigInteger, DateTime, CHAR, Index
)
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB  # ← ใช้ JSONB
from sqlalchemy.orm import relationship

from app.database import Base


# ===== Enums mapping =====
class UserRole(str, Enum):
    user = "user"
    admin = "admin"

class TicketStatus(str, Enum):
    open = "open"
    awaiting_payment = "awaiting_payment"
    payment_held = "payment_held"
    awaiting_delivery = "awaiting_delivery"
    in_review = "in_review"
    completed = "completed"
    cancelled = "cancelled"
    disputed = "disputed"
    refunded = "refunded"

class PaymentStatus(str, Enum):
    pending = "pending"
    held = "held"
    released = "released"
    refunded = "refunded"
    failed = "failed"


# ===== Users =====
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(CITEXT, unique=True, nullable=False)
    username = Column(CITEXT, unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(PgEnum(UserRole, name="user_role"), nullable=False, default=UserRole.user)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ===== Tickets =====
class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text)
    opener_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(PgEnum(TicketStatus, name="ticket_status"), nullable=False, default=TicketStatus.open)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime(timezone=True))

    messages = relationship("TicketMessage", back_populates="ticket", cascade="all,delete")
    payments = relationship("EscrowPayment", back_populates="ticket", cascade="all,delete")
    logs = relationship("ActivityLog", back_populates="ticket", cascade="all,delete")


Index("idx_tickets_status", Ticket.status)
Index("idx_tickets_buyer", Ticket.buyer_id)
Index("idx_tickets_seller", Ticket.seller_id)
Index("idx_tickets_created_at", Ticket.created_at)


# ===== Ticket messages =====
class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body = Column(Text, nullable=False)
    attachments = Column(JSONB)  # ← เปลี่ยนเป็น JSONB
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="messages")


# ===== Escrow payments =====
class EscrowPayment(Base):
    __tablename__ = "escrow_payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    payer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    currency = Column(CHAR(3), nullable=False, default="THB")
    status = Column(PgEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.pending)
    provider = Column(Text, nullable=True, default="manual")  # ← ใส่ default ให้สอดคล้องกับการสร้าง escrow อัตโนมัติ
    provider_ref = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    released_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))

    ticket = relationship("Ticket", back_populates="payments")


# ===== Activity Logs =====
class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="SET NULL"))
    action = Column(Text, nullable=False)
    meta = Column(JSONB)  # ← เปลี่ยนเป็น JSONB
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="logs")
