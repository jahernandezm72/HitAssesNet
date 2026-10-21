from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .db import Base, SessionLocal, engine
from .models import User
from .routes import router
from .security import hash_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # POC: tablas automáticas. En producción usar Alembic.
    with SessionLocal() as db:
        if not db.scalar(select(User).limit(1)):
            db.add(User(email=settings.admin_email.lower(), name=settings.admin_name,
                        password_hash=hash_password(settings.admin_password), role="admin"))
            db.commit()
    yield


app = FastAPI(title="HitAssesNet API", version="0.1.0", lifespan=lifespan)
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                       allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

if settings.static_dir:  # modo sin nginx: la API sirve landing y app
    from fastapi.staticfiles import StaticFiles
    app.mount("/app", StaticFiles(directory=f"{settings.static_dir}/app", html=True), name="app")
    app.mount("/", StaticFiles(directory=f"{settings.static_dir}/landing", html=True), name="landing")
