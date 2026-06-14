import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, groups, expenses, settlements, balances, imports

# Auto-create tables on startup (PostgreSQL or SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Shared Expense Management & CSV Import Analysis",
    version="1.0.0"
)

# CORS configuration — reads from ALLOWED_ORIGINS env var (comma-separated) or defaults to *
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if _raw_origins == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(settlements.router, prefix="/api")
app.include_router(balances.router, prefix="/api")
app.include_router(imports.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Split Expenser API. Navigate to /docs for Swagger UI."}
