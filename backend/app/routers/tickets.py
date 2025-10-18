# app/routers/tickets.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, constr
from typing import Optional, List, Literal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

# ใช้สคีมาใหม่: สร้างด้วย username ของอีกฝั่ง
from app.schemas import TicketCreateByName, TicketCreateOut

# get_db ตามโปรเจกต์คุณ
from app.database import get_db
# ดึง user ปัจจุบันจาก JWT
from app.auth import get_current_user  # ต้องมีฟังก์ชันนี้แล้วในโปรเจกต์คุณ

router = APIRouter(prefix="/tickets", tags=["tickets"])


# =========== Schemas (สำหรับ response/endpoint อื่น ๆ เดิม) ===========
class TicketOut(BaseModel):
    ticket_id: str

class TicketDetail(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str

class MessageOut(BaseModel):
    id: str
    ticket_id: str
    sender_id: str
    body: str
    created_at: str

class SendMessageIn(BaseModel):
    # NOTE: ยังคง sender_id ไว้เพื่อไม่ทำให้หน้าแชทเดิมพัง (ถ้าจะให้ปลอดภัยกว่านี้ แนะนำย้ายไปใช้ current_user)
    sender_id: constr(min_length=36, max_length=36)
    body: constr(min_length=1)


# =========== Helpers ===========
def _ensure_user_exists(db: Session, user_id: str, field_name: str):
    row = db.execute(text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id}).first()
    if not row:
        raise HTTPException(status_code=400, detail=f"{field_name} not found")


# =========== Endpoints ===========
@router.post("", response_model=TicketCreateOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreateByName,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    สร้าง Ticket โดย:
    - current_user จาก JWT เป็น opener
    - กำหนด buyer/seller จาก role
    - หาอีกฝั่งด้วย counterparty_username
    - สร้าง escrow_payments (pending) ทันที โดยกำหนด payer = buyer
    - ถ้ามี first_message ให้สร้างข้อความแรกในห้อง
    """
    # หาอีกฝั่งจาก username (CITEXT)
    row_cp = db.execute(
        text("SELECT id::text FROM users WHERE username = :u LIMIT 1"),
        {"u": payload.counterparty_username},
    ).first()
    if not row_cp:
        raise HTTPException(status_code=400, detail="counterparty_username not found")

    opener_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)
    counterparty_id = row_cp[0]

    if counterparty_id == opener_id:
        raise HTTPException(status_code=400, detail="counterparty cannot be yourself")

    # map บทบาท -> buyer/seller
    if payload.role == "buyer":
        buyer_id = opener_id
        seller_id = counterparty_id
    else:
        seller_id = opener_id
        buyer_id = counterparty_id

    # ---- CREATE TICKET ----
    row_t = db.execute(text("""
        INSERT INTO tickets (title, description, opener_id, buyer_id, seller_id)
        VALUES (:title, :description, :opener_id, :buyer_id, :seller_id)
        RETURNING id::text
    """), {
        "title": payload.title,
        "description": payload.description,
        "opener_id": opener_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
    }).first()
    if not row_t:
        raise HTTPException(status_code=500, detail="failed to insert ticket")
    ticket_id = row_t[0]

    # ---- LOG: CREATE_TICKET ----
    db.execute(text("""
        INSERT INTO activity_logs (actor_id, ticket_id, action, meta)
        VALUES (:actor_id, :ticket_id, 'CREATE_TICKET',
                jsonb_build_object(
                    'game', :game, 'role', :role,
                    'price_cents', :price_cents, 'currency', :currency,
                    'counterparty_username', :counterparty
                ))
    """), {
        "actor_id": opener_id,
        "ticket_id": ticket_id,
        "game": payload.game,
        "role": payload.role,
        "price_cents": payload.price_cents,
        "currency": payload.currency,
        "counterparty": payload.counterparty_username
    })

    # ---- CREATE ESCROW (PENDING) ----
    # If price is zero, skip creating an escrow record (DB has a CHECK that amount_cents > 0)
    escrow_id = None
    if payload.price_cents and payload.price_cents > 0:
        row_e = db.execute(text("""
            INSERT INTO escrow_payments (ticket_id, payer_id, amount_cents, currency, status, provider)
            VALUES (:ticket_id, :payer_id, :amount_cents, :currency, 'pending', 'manual')
            RETURNING id::text
        """), {
            "ticket_id": ticket_id,
            "payer_id": buyer_id,                # ผู้ชำระคือ buyer
            "amount_cents": payload.price_cents,
            "currency": payload.currency,
        }).first()
        escrow_id = row_e[0]

    # ---- LOG: ESCROW_PENDING ----
    db.execute(text("""
        INSERT INTO activity_logs (actor_id, ticket_id, action, meta)
        VALUES (:actor_id, :ticket_id, 'ESCROW_PENDING',
                jsonb_build_object('escrow_id', :escrow_id, 'amount_cents', :amount_cents, 'currency', :currency))
    """), {
        "actor_id": buyer_id,                # ผู้ดำเนินการคือฝั่งคนจ่าย
        "ticket_id": ticket_id,
        "escrow_id": escrow_id,
        "amount_cents": payload.price_cents,
        "currency": payload.currency,
    })

    # ---- FIRST MESSAGE (optional) ----
    if payload.first_message:
        db.execute(text("""
            INSERT INTO ticket_messages (ticket_id, sender_id, body, attachments)
            VALUES (:ticket_id, :sender_id, :body, NULL)
        """), {
            "ticket_id": ticket_id,
            "sender_id": opener_id,
            "body": payload.first_message
        })

    db.commit()
    return {"ticket_id": ticket_id}


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT id::text, title, description, status::text
        FROM tickets
        WHERE id = :tid
    """), {"tid": ticket_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="ticket not found")
    return TicketDetail(id=row[0], title=row[1], description=row[2], status=row[3])


@router.get("/{ticket_id}/messages", response_model=List[MessageOut])
def list_messages(ticket_id: UUID, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id::text, ticket_id::text, sender_id::text, body,
               to_char(created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created_at
        FROM ticket_messages
        WHERE ticket_id = :tid
        ORDER BY created_at ASC
    """), {"tid": ticket_id}).fetchall()
    return [
        MessageOut(
            id=r[0], ticket_id=r[1], sender_id=r[2], body=r[3], created_at=r[4]
        ) for r in rows
    ]


@router.post("/{ticket_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(ticket_id: UUID, payload: SendMessageIn, db: Session = Depends(get_db)):
    # NOTE: ถ้าจะให้ปลอดภัยกว่านี้ แนะนำเปลี่ยนมาใช้ current_user จาก JWT แล้วเอา sender_id จาก token
    # current_user = Depends(get_current_user); sender_id = current_user.id
    # ที่นี่คง sender_id ไว้เพื่อไม่พังของเดิม
    _ensure_user_exists(db, payload.sender_id, "sender_id")

    t = db.execute(text("SELECT 1 FROM tickets WHERE id = :id"), {"id": ticket_id}).first()
    if not t:
        raise HTTPException(status_code=404, detail="ticket not found")

    row = db.execute(text("""
        INSERT INTO ticket_messages (ticket_id, sender_id, body, attachments)
        VALUES (:ticket_id, :sender_id, :body, NULL)
        RETURNING id::text,
                  ticket_id::text,
                  sender_id::text,
                  body,
                  to_char(created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created_at
    """), {
        "ticket_id": ticket_id,
        "sender_id": payload.sender_id,
        "body": payload.body
    }).first()

    db.execute(text("""
        INSERT INTO activity_logs (actor_id, ticket_id, action, meta)
        VALUES (:actor_id, :ticket_id, 'SEND_MESSAGE', NULL)
    """), {"actor_id": payload.sender_id, "ticket_id": ticket_id})

    db.commit()

    return MessageOut(
        id=row[0], ticket_id=row[1], sender_id=row[2], body=row[3], created_at=row[4]
    )
