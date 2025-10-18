import os, datetime as dt
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session
from passlib.hash import bcrypt_sha256   # <<< ใช้ตัวนี้แทน bcrypt ปกติ
from .database import SessionLocal
from .models import User
import uuid

# simple HTTP Bearer for dependency
_bearer_scheme = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(pw: str) -> str:
    # รองรับความยาวเกิน 72 bytes ได้
    return bcrypt_sha256.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    return bcrypt_sha256.verify(pw, pw_hash)

def create_token(user_id: int) -> str:
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def find_user_by_email(db: Session, email: str):
    """Return a User by email or None."""
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    Decode the Bearer JWT and return the User SQLAlchemy object.
    Raises 401 if token invalid or user not found.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        user_id = uuid.UUID(str(sub))
    except Exception:
        # fallback: try plain string
        user_id = str(sub)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
