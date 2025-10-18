# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # ค่านี้ใช้ตอนรันใน docker compose (service name: db, port 5432)
    "postgresql+psycopg2://game:game@db:5433/tradingzone"
)

# ถ้าคุณรัน local (นอก docker) และแมปพอร์ตไว้ 5433:
# export DATABASE_URL=postgresql+psycopg2://game:game@localhost:5433/tradingzone

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
