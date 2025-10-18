from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine

# Import all routers
from app.routers import tickets as tickets_router
from app.routers import auth as auth_router
from app.routers import health as health_router

# สร้างตาราง (dev: auto create; prod: ควรใช้ Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TradingZone API",
    version="1.1.8",
    description="Backend for TradingZone — tickets, auth, chats, escrow.",
)

# DEV CORS — ปล่อยทุก origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # เปลี่ยนเป็น URL frontend จริงในโปรดักชัน
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# รวม router
try:
    app.include_router(tickets_router.router)
    print("[DEBUG] tickets router included")
except Exception as e:
    import traceback
    print("[DEBUG] tickets router FAILED to import:", e)
    traceback.print_exc()

try:
    app.include_router(auth_router.router)
    print("[DEBUG] auth router included")
except Exception as e:
    import traceback
    print("[DEBUG] auth router FAILED to import:", e)
    traceback.print_exc()

try:
    app.include_router(health_router.router)
    print("[DEBUG] health router included")
except Exception as e:
    import traceback
    print("[DEBUG] health router FAILED to import:", e)
    traceback.print_exc()


@app.get("/")
async def root():
    return {"status": "ok", "service": "TradingZone API", "version": app.version}


# Debug: พิมพ์ route ทั้งหมดตอนบู๊ต (ช่วยเช็คว่ามี /tickets โผล่)
def _dump_routes():
    print("[ROUTES DUMP]")
    for r in app.routes:
        m = getattr(r, "methods", None)
        p = getattr(r, "path", None)
        if m and p:
            print(" ", m, p)

_dump_routes()
