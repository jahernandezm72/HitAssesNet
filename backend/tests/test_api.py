import uuid


def lead(company="Clínica Valle", **kw):
    d = {"id": str(uuid.uuid4()), "company": company, "contact": "Dr. Pérez", "phone": "956", "city": "McAllen",
         "vertical": "salud", "territory": "valle", "plan": 1, "users": 20, "filial": "", "stage": 0,
         "next_step": "Llamar", "next_date": "2026-11-01", "notes": ""}
    d.update(kw)
    return d


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "db": True}


def test_auth_required(client):
    assert client.get("/api/bootstrap").status_code == 401
    assert client.get("/api/bootstrap", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_login_ok_and_fail(client):
    assert client.post("/api/auth/login", json={"email": "admin@test.local", "password": "mala"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "ADMIN@test.local", "password": "AdminPass12345"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin"


def test_login_rate_limit(client):
    codes = [client.post("/api/auth/login", json={"email": "admin@test.local", "password": "x"}).status_code for _ in range(10)]
    assert codes[:8] == [401] * 8 and codes[8] == 429


def test_costs_admin_only_and_roundtrip(client, admin, vendedor):
    items = [{"category": "Personal", "name": "Ingeniero", "usd": 2000, "share_pct": 100},
             {"category": "Administrativo", "name": "Oficina", "usd": 800, "share_pct": 50}]
    assert client.put("/api/costs", headers=vendedor, json={"items": items}).status_code == 403
    assert client.put("/api/costs", headers=admin, json={"items": items}).status_code == 200
    b = client.get("/api/bootstrap", headers=admin).json()
    assert [c["name"] for c in b["costs"]] == ["Ingeniero", "Oficina"] and b["costs"][1]["share_pct"] == 50
    assert client.get("/api/bootstrap", headers=vendedor).json()["costs"] is None  # el vendedor no ve costos


def test_params_visibility(client, admin, vendedor):
    p = {"fx": 18.35, "tm": 35, "mf": 250, "com": 10, "vc": [30, 45, 70], "tf": {"nl": 1.1}}
    assert client.put("/api/params", headers=vendedor, json=p).status_code == 403
    assert client.put("/api/params", headers=admin, json=p).status_code == 200
    v = client.get("/api/bootstrap", headers=vendedor).json()
    assert v["fx"] == 18.35 and v["tf"] == {"nl": 1.1} and v["params"] is None  # margen/comisión solo admin
    assert client.get("/api/bootstrap", headers=admin).json()["params"]["com"] == 10


def test_params_validation(client, admin):
    bad = {"fx": 0, "tm": 35, "mf": 250, "com": 10, "vc": [1, 2, 3]}
    assert client.put("/api/params", headers=admin, json=bad).status_code == 422
    bad = {"fx": 18, "tm": 35, "mf": 250, "com": 10, "vc": [1, 2, 3], "tf": {"narnia": 1}}
    assert client.put("/api/params", headers=admin, json=bad).status_code == 422


def test_leads_sync_upsert_delete(client, admin, vendedor):
    a, b = lead("A"), lead("B")
    assert client.put("/api/leads", headers=vendedor, json={"leads": [a, b]}).status_code == 200
    got = client.get("/api/bootstrap", headers=vendedor).json()["leads"]
    assert {l["company"] for l in got} == {"A", "B"}
    a["stage"] = 5
    assert client.put("/api/leads", headers=vendedor, json={"leads": [a]}).status_code == 200  # B desaparece
    got = client.get("/api/bootstrap", headers=vendedor).json()["leads"]
    assert [(l["company"], l["stage"]) for l in got] == [("A", 5)]


def test_leads_scoping(client, admin, vendedor):
    mine = lead("Del socio")
    client.put("/api/leads", headers=vendedor, json={"leads": [mine]})
    adm = lead("Del admin")
    client.put("/api/leads", headers=admin, json={"leads": [mine, adm]})
    assert {l["company"] for l in client.get("/api/bootstrap", headers=admin).json()["leads"]} == {"Del socio", "Del admin"}
    assert [l["company"] for l in client.get("/api/bootstrap", headers=vendedor).json()["leads"]] == ["Del socio"]
    # el vendedor no puede tomar ni pisar un prospecto ajeno
    assert client.put("/api/leads", headers=vendedor, json={"leads": [adm]}).status_code == 403


def test_leads_validation(client, vendedor):
    assert client.put("/api/leads", headers=vendedor, json={"leads": [lead(plan=9)]}).status_code == 422
    assert client.put("/api/leads", headers=vendedor, json={"leads": [lead(territory="mars")]}).status_code == 422
    assert client.put("/api/leads", headers=vendedor, json={"leads": [lead(next_date="mañana")]}).status_code == 422


def test_assessment_per_user(client, admin, vendedor):
    client.put("/api/assessment", headers=vendedor, json={"data": {"company": "X", "employees": "12"}, "prop": {"disc": 5}})
    v = client.get("/api/bootstrap", headers=vendedor).json()["assessment"]
    assert v["data"]["company"] == "X" and v["prop"] == {"disc": 5}
    assert client.get("/api/bootstrap", headers=admin).json()["assessment"]["data"] == {}  # cada quien el suyo


def test_checks_shared(client, admin, vendedor):
    client.put("/api/checks", headers=vendedor, json={"checks": {"c1": True}})
    assert client.get("/api/bootstrap", headers=admin).json()["checks"] == {"c1": True}


def test_public_contact_creates_lead_for_admin(client, admin, vendedor):
    body = {"name": "Ana", "company": "Maquila Norte", "email": "ana@maquila.com", "phone": "956", "users": 30, "message": "Quiero assessment"}
    assert client.post("/api/public/contact", json=body).status_code == 201
    adm = client.get("/api/bootstrap", headers=admin).json()["leads"]
    assert adm[0]["company"] == "Maquila Norte" and adm[0]["source"] == "landing" and "ana@maquila.com" in adm[0]["notes"]
    assert client.get("/api/bootstrap", headers=vendedor).json()["leads"] == []


def test_public_contact_honeypot_and_limit(client, admin):
    base = {"name": "Bot", "company": "Spam", "email": "b@b.com"}
    assert client.post("/api/public/contact", json={**base, "website": "http://spam"}).status_code == 201
    assert client.get("/api/bootstrap", headers=admin).json()["leads"] == []  # no se guardó
    codes = [client.post("/api/public/contact", json={**base, "company": f"E{i}"}).status_code for i in range(6)]
    assert codes[-1] == 429


def test_user_management(client, admin, vendedor):
    assert client.get("/api/users", headers=vendedor).status_code == 403
    dup = {"email": "socio@test.local", "name": "Otro", "password": "OtraPass123456"}
    assert client.post("/api/users", headers=admin, json=dup).status_code == 409
    assert client.post("/api/users", headers=admin, json={**dup, "email": "x@test.local", "password": "corta"}).status_code == 422
