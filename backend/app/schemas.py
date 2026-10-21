from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints

# Correo flexible para cuentas internas (acepta dominios como .local); el formulario público usa EmailStr estricto
LooseEmail = Annotated[str, StringConstraints(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$', max_length=254)]

Territory = Literal["valle", "sa", "dfw", "hou", "nl", "chi", "coa", "tam"]
Vertical = Literal["salud", "pyme", "ind", "retail"]
Category = Literal["Personal", "Herramientas", "Administrativo", "Comercial"]


class LoginIn(BaseModel):
    email: LooseEmail
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class UserCreate(BaseModel):
    email: LooseEmail
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=72)
    role: Literal["admin", "vendedor"] = "vendedor"


class CostItemIO(BaseModel):
    category: Category
    name: str = Field(max_length=200)
    usd: float = Field(ge=0, le=10_000_000)
    share_pct: float = Field(ge=0, le=100)


class CostsIn(BaseModel):
    items: list[CostItemIO] = Field(max_length=200)


class ParamsIn(BaseModel):
    fx: float = Field(gt=0, le=1000)
    tm: float = Field(ge=0, le=100)
    mf: float = Field(ge=0, le=1_000_000)
    com: float = Field(ge=0, le=100)
    vc: list[float] = Field(min_length=3, max_length=3)
    tf: dict[Territory, float] = {}


class LeadIO(BaseModel):
    id: str = Field(min_length=8, max_length=36)
    company: str = Field(min_length=1, max_length=200)
    contact: str = Field("", max_length=200)
    phone: str = Field("", max_length=60)
    city: str = Field("", max_length=120)
    vertical: Vertical = "pyme"
    territory: Territory = "valle"
    plan: int = Field(1, ge=0, le=2)
    users: int = Field(10, ge=1, le=100_000)
    filial: str = Field("", max_length=40)
    stage: int = Field(0, ge=0, le=6)
    next_step: str = Field("", max_length=300)
    next_date: str = Field("", pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    notes: str = Field("", max_length=4000)


class LeadsIn(BaseModel):
    leads: list[LeadIO] = Field(max_length=5000)


class AssessmentIn(BaseModel):
    data: dict
    prop: dict | None = None


class ChecksIn(BaseModel):
    checks: dict[str, bool]


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field("", max_length=60)
    city: str = Field("", max_length=120)
    users: int = Field(10, ge=1, le=100_000)
    message: str = Field("", max_length=2000)
    website: str = Field("", max_length=200)  # honeypot: debe ir vacío
