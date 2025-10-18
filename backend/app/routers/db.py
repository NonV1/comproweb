# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ใช้ DATABASE_URL จาก env ของคุณ
# เช่น postgresql+psycopg2://game:game@db:5433/tradingzone
from app.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
