import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from . import schemas
from .db import get_db
from .models import Assessment, CostItem, Lead, Setting, User
from .security import (admin_only, client_ip, create_token, current_user, hash_password,
                       rate_limit, verify_password)

router = APIRouter(prefix="/api")
MAX_JSON_BYTES = 200_000


def _setting(db: Session, key: str):
    row = db.get(Setting, key)
    return row.value if row else None


def _put_setting(db: Session, key: str, value: dict):
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def _size_ok(obj) -> None:
    if len(json.dumps(obj)) > MAX_JSON_BYTES:
        raise HTTPException(413, "Datos demasiado grandes")


def _lead_out(l: Lead) -> dict:
    return {
        "id": l.id, "company": l.company, "contact": l.contact, "phone": l.phone, "city": l.city,
        "vertical": l.vertical, "territory": l.territory, "plan": l.plan, "users": l.users,
        "filial": l.filial, "stage": l.stage, "next_step": l.next_step, "next_date": l.next_date,
        "notes": l.notes, "source": l.source,
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok", "db": True}


@router.post("/auth/login")
def login(body: schemas.LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"login:{client_ip(request)}:{body.email.lower()}", 8, 300)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return {"token": create_token(user), "user": schemas.UserOut(id=user.id, email=user.email, name=user.name, role=user.role)}


@router.get("/auth/me", response_model=schemas.UserOut)
def me(user: User = Depends(current_user)):
    return schemas.UserOut(id=user.id, email=user.email, name=user.name, role=user.role)


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [schemas.UserOut(id=u.id, email=u.email, name=u.name, role=u.role) for u in db.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Ese correo ya existe")
    u = User(email=email, name=body.name, password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    db.commit()
    return schemas.UserOut(id=u.id, email=u.email, name=u.name, role=u.role)


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user: User = Depends(current_user)):
    admin = user.role == "admin"
    params = _setting(db, "params")
    out = {
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        "fx": (params or {}).get("fx"),
        "tf": (params or {}).get("tf"),
        "params": ({k: params[k] for k in ("tm", "mf", "com", "vc") if k in params} if admin and params else None),
        "costs": None,
        "checks": (_setting(db, "checks") or {}).get("checks", {}),
    }
    if admin:
        rows = db.scalars(select(CostItem).order_by(CostItem.position, CostItem.id)).all()
        out["costs"] = [{"category": r.category, "name": r.name, "usd": float(r.usd), "share_pct": float(r.share_pct)} for r in rows]
    q = select(Lead).order_by(Lead.created_at)
    if not admin:
        q = q.where(Lead.owner_id == user.id)
    out["leads"] = [_lead_out(l) for l in db.scalars(q)]
    a = db.scalar(select(Assessment).where(Assessment.owner_id == user.id))
    out["assessment"] = {"data": a.data, "prop": a.prop} if a else {"data": {}, "prop": None}
    return out


@router.put("/costs")
def put_costs(body: schemas.CostsIn, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    db.execute(delete(CostItem))
    for i, it in enumerate(body.items):
        db.add(CostItem(category=it.category, name=it.name, usd=it.usd, share_pct=it.share_pct, position=i))
    db.commit()
    return {"saved": len(body.items)}


@router.put("/params")
def put_params(body: schemas.ParamsIn, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    _put_setting(db, "params", body.model_dump())
    db.commit()
    return {"saved": True}


@router.put("/checks")
def put_checks(body: schemas.ChecksIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _size_ok(body.checks)
    _put_setting(db, "checks", {"checks": body.checks})
    db.commit()
    return {"saved": True}


@router.put("/assessment")
def put_assessment(body: schemas.AssessmentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _size_ok(body.model_dump())
    a = db.scalar(select(Assessment).where(Assessment.owner_id == user.id))
    if a:
        a.data, a.prop = body.data, body.prop
    else:
        db.add(Assessment(owner_id=user.id, data=body.data, prop=body.prop))
    db.commit()
    return {"saved": True}


@router.put("/leads")
def put_leads(body: schemas.LeadsIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Sincroniza la lista visible para el usuario: crea/actualiza los recibidos y elimina los que ya no vienen."""
    admin = user.role == "admin"
    scope = select(Lead) if admin else select(Lead).where(Lead.owner_id == user.id)
    existing = {l.id: l for l in db.scalars(scope)}
    incoming_ids = {l.id for l in body.leads}
    for l in body.leads:
        row = existing.get(l.id)
        if row is None:
            if db.get(Lead, l.id):  # id existe pero pertenece a otro usuario
                raise HTTPException(403, "Prospecto de otro usuario")
            row = Lead(id=l.id, owner_id=user.id)
            db.add(row)
        for k, v in l.model_dump(exclude={"id"}).items():
            setattr(row, k, v)
    for lid, row in existing.items():
        if lid not in incoming_ids:
            db.delete(row)
    db.commit()
    return {"saved": len(body.leads)}


@router.post("/public/contact", status_code=201)
def public_contact(body: schemas.ContactIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"contact:{client_ip(request)}", 5, 3600)
    if body.website:  # honeypot: un bot rellenó el campo oculto
        return {"ok": True}
    notes = f"Email: {body.email}\n{body.message}".strip()
    db.add(Lead(id=str(uuid.uuid4()), owner_id=None, company=body.company, contact=body.name, phone=body.phone,
                email=str(body.email), city=body.city, users=body.users, stage=0,
                next_step="Contactar desde landing", notes=notes, source="landing"))
    db.commit()
    return {"ok": True}
