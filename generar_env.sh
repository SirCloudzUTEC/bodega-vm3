#!/usr/bin/env bash
# Crea .env con 5 contraseñas aleatorias (hexadecimales: sin caracteres que rompan URIs).
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .env ]; then echo ".env ya existe: no se sobrescribe (bórralo a mano si de verdad quieres regenerarlo)."; exit 0; fi
clave() { od -vAn -N24 -tx1 /dev/urandom | tr -d ' \n'; }
umask 077
cat > .env <<EOT
MYSQL_ROOT_PASSWORD=$(clave)
MYSQL_PASSWORD=$(clave)
POSTGRES_PASSWORD=$(clave)
MONGO_ROOT_PASSWORD=$(clave)
MONGO_PASSWORD=$(clave)
EOT
echo ".env creado (permisos 600)."
echo "Copia estas 3 líneas al .env de Backend A, Backend B y VM4:"
grep -E '^(MYSQL|POSTGRES|MONGO)_PASSWORD=' .env
