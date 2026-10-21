# HitAssesNet — Network Assessment, cotizador y pipeline MSP (HERMOIT)

POC full-stack para la campaña MSP Q4 2026–Q1 2027 (Texas y filiales en México).

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL 17 |
| Backend | FastAPI + SQLAlchemy 2 + JWT (roles `admin` / `vendedor`) |
| Frontend | Portal web en `web/app` (HTML + JS, sin build) |
| Landing | `web/landing` (ES/EN, formulario → pipeline) |
| Proxy | nginx (`/` landing · `/app/` portal · `/api/` backend) |
| Despliegue | Docker Compose (POC en Ubuntu Server → Coolify/Hetzner) |

## Qué hace
- **Catálogo y cotizador** por territorio (Valle, San Antonio, DFW, Houston; filiales en NL, Chihuahua, Coahuila, Tamaulipas en MXN), con cotización binacional.
- **Network Assessment** (10 secciones) con índice de riesgo y **propuesta recomendada** con 3 opciones; el cliente puede quitar adicionales.
- **Pipeline de prospectos**, checklist de campaña y costos USA editables (con % que paga HERMOIT y el socio).
- **Roles**: `admin` ve costos, parámetros y márgenes; `vendedor` solo ve catálogo, cotizador, assessment, propuesta y **sus** prospectos.
- La landing guarda las solicitudes como prospectos sin asignar (visibles para `admin`).

## Instalación en Ubuntu Server (26.04 LTS)
```bash
git clone https://github.com/jahernandezm72/HitAssesNet.git && cd HitAssesNet
sudo ./scripts/install_ubuntu.sh
```
El script instala Docker, genera `.env` con secretos aleatorios, levanta `db`, `api` y `web` y muestra las URLs y el usuario admin.

Manual: `cp .env.example .env` (edita las claves) y `docker compose up -d --build`.

## Modo nativo (sin Docker)
```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@localhost:5432/hitassesnet STATIC_DIR=../web
uvicorn app.main:app --port 8000      # landing en / y portal en /app/
```

## Pruebas
```bash
cd backend && DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@localhost:5432/hitassesnet_test pytest -q
```
(Usa una base de datos de prueba: las pruebas borran sus tablas.)

## Usuarios
El primer arranque crea el admin con `ADMIN_EMAIL`/`ADMIN_PASSWORD`. Crear un vendedor:
```bash
TOKEN=$(curl -s localhost/api/auth/login -H 'Content-Type: application/json' -d '{"email":"ADMIN","password":"CLAVE"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s localhost/api/users -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"email":"socio@dominio.com","name":"Socio Valle","password":"clave-de-10-o-mas","role":"vendedor"}'
```

## Migración a Hetzner + Coolify (después de las pruebas)
1. En Coolify: nuevo recurso → Docker Compose desde este repo (o servicios separados con `backend/` y `web/`).
2. Variables: `ENV=prod`, `POSTGRES_*`, `JWT_SECRET`, `ADMIN_*` (en `prod` la API no arranca con valores por defecto).
3. Dominio `hermoit.cloud` en Cloudflare → Coolify con TLS; quita la publicación directa del puerto 80 si usas el proxy de Coolify.
4. Respaldos de PostgreSQL (volumen `pgdata`) a almacenamiento externo y prueba de restauración.

## Límites conocidos del POC (pendientes antes de producción)
- Las tablas se crean al arrancar (`create_all`); falta **Alembic** para migraciones.
- Los cálculos de cotización y recomendación viven en el navegador. Un vendedor técnico podría ver en el código los parámetros por defecto de margen; para confidencialidad real hay que mover el cálculo al backend.
- La sincronización de prospectos reemplaza la lista del usuario: si dos sesiones del mismo usuario editan a la vez, gana la última.
- Los prospectos que llegan por la landing quedan sin asignar (solo admin); falta pantalla de asignación.
- El límite de intentos de login/contacto es en memoria (un solo proceso); en producción usar el proxy o Redis.
- Frontend en HTML/JS simple; la plataforma final prevista (Angular + Tailwind + SSR, Supabase) es una migración posterior.
