from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, constr, conint, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=32)
    password: constr(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    # NOTE: แก้ให้ถูกกับ DB จริง — users.id เป็น UUID
    id: UUID
    email: EmailStr
    username: str


# ---------- Ticket (เวอร์ชันใหม่: สร้างด้วย username ของอีกฝั่ง) ----------
class TicketCreateByName(BaseModel):
    """
    ใช้สำหรับสร้าง Ticket โดย:
    - current_user มาจาก JWT (ฝั่ง API ดึงเอง)
    - กรอกชื่ออีกฝั่ง (counterparty_username) แทน UUID
    - role: current_user เป็น buyer หรือ seller
    """
    title: constr(min_length=3, max_length=120)
    description: Optional[str] = None
    role: Literal["buyer", "seller"]
    game: constr(min_length=2, max_length=50)
    price_cents: conint(ge=0) = Field(..., description="ราคาเป็นหน่วยย่อย เช่น 159000 = 1,590.00")
    currency: constr(min_length=3, max_length=3) = "THB"
    counterparty_username: constr(min_length=3, max_length=32)
    first_message: Optional[str] = None


class TicketCreateOut(BaseModel):
    ticket_id: UUID


# Backwards-compatible aliases: some routers/docs expect the older names
# Make `TicketCreate` point to the new `TicketCreateByName` so OpenAPI
# and any imports using the old name will see the updated schema.
TicketCreate = TicketCreateByName
# The project previously exposed `TicketOut` as the response model name;
# alias it to the new `TicketCreateOut` to keep compatibility.
TicketOut = TicketCreateOut


# Backwards-compatible explicit model: old endpoints expect a `TicketCreate`
# payload with opener_id / buyer_id / seller_id fields. Define it here to
# ensure OpenAPI uses the updated constraint (price_cents >= 0) regardless
# of where a `TicketCreate` name may be referenced.
class TicketCreate(BaseModel):
    title: constr(min_length=3, max_length=120)
    description: Optional[str] = None
    opener_id: UUID
    role: Literal["buyer", "seller"]
    game: constr(min_length=2, max_length=50)
    price_cents: conint(ge=0) = Field(..., description="ราคาเป็นหน่วยย่อย เช่น 159000 = 1,590.00")
    currency: constr(min_length=3, max_length=3) = "THB"
    buyer_id: Optional[UUID] = None
    seller_id: Optional[UUID] = None
    first_message: Optional[str] = None





