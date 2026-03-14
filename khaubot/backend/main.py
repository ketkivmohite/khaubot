from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

from database import create_db_and_tables
from routers import vendors, discover


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    create_db_and_tables()
    print("✅ KhauBot backend started. DB ready.")
    yield
    # Runs on shutdown
    print("👋 KhauBot backend shutting down.")


app = FastAPI(
    title="KhauBot API",
    description="AI-powered hyperlocal food discovery for Mumbai 🍛",
    version="1.0.0",
    lifespan=lifespan
)

# Allow Django frontend to talk to this API
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8002")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(vendors.router, prefix="/api/vendor", tags=["Vendor"])
app.include_router(discover.router, prefix="/api", tags=["Discovery"])


@app.get("/")
def root():
    return {"message": "KhauBot is live 🍜 Mumbai ka food, digital ho gaya!"}