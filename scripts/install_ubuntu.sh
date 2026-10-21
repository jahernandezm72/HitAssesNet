#!/usr/bin/env bash
# Instala el POC de HitAssesNet en Ubuntu Server (objetivo: 26.04 LTS; también sirve en 24.04).
# Uso:  sudo ./scripts/install_ubuntu.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }
. /etc/os-release
echo ">> Sistema: ${PRETTY_NAME}"

echo ">> Instalando Docker (paquetes oficiales de Ubuntu)..."
apt-get update -y
apt-get install -y docker.io docker-compose-v2 curl openssl
systemctl enable --now docker

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ">> Generando .env con secretos aleatorios..."
  cp .env.example .env
  PG=$(openssl rand -hex 16); JWT=$(openssl rand -hex 32); ADM="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-14)Aa1"
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG}|; s|^JWT_SECRET=.*|JWT_SECRET=${JWT}|; s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADM}|" .env
  chmod 600 .env
fi

PORT=$(grep -E '^HTTP_PORT=' .env | cut -d= -f2); PORT=${PORT:-80}
echo ">> Levantando servicios (db, api, web)..."
docker compose up -d --build

echo ">> Esperando a que la API responda..."
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then OK=1; break; fi
  sleep 3
done
[ "${OK:-0}" = "1" ] || { echo "La API no respondió. Revisa: docker compose logs api db"; exit 1; }

IP=$(hostname -I | awk '{print $1}')
echo
echo "=== Listo ==="
echo "Landing : http://${IP}:${PORT}/"
echo "Portal  : http://${IP}:${PORT}/app/"
echo "Admin   : $(grep ADMIN_EMAIL .env | cut -d= -f2)  /  $(grep ADMIN_PASSWORD .env | cut -d= -f2)"
echo "Guarda esa contraseña y crea los usuarios vendedor desde el portal/API (POST /api/users)."
