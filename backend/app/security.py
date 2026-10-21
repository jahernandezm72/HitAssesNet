import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_hours)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if not creds:
        raise HTTPException(401, "No autenticado")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Sesión inválida o vencida")
    if not user or not user.active:
        raise HTTPException(401, "Usuario inactivo")
    return user


def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Solo administradores")
    return user


# Límite de intentos en memoria (suficiente para el POC; en producción usar Redis o el proxy)
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(key: str, max_hits: int, window_s: int):
    t = time.time()
    _hits[key] = [x for x in _hits[key] if t - x < window_s]
    if len(_hits[key]) >= max_hits:
        raise HTTPException(429, "Demasiados intentos, espera unos minutos")
    _hits[key].append(t)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
