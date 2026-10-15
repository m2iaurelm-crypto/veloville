#!/usr/bin/env bash
# Sauvegarde horodatée de la base configurée dans .env.
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/sauvegardes}"

if [[ ! -f "$ENV_FILE" ]]; then
	echo "Fichier .env introuvable à la racine du projet." >&2
	exit 1
fi

if [[ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
	PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
	PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
	PYTHON="${PYTHON:-python}"
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/veloville_$(date +%Y%m%d_%H%M%S).dump"
if [[ -e "$BACKUP_FILE" ]]; then
	echo "Une sauvegarde porte déjà ce nom : $BACKUP_FILE" >&2
	exit 1
fi

"$PYTHON" - "$ENV_FILE" "$BACKUP_FILE" <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit

from dotenv import dotenv_values

env_file, backup_file = map(Path, sys.argv[1:])
database_url = dotenv_values(env_file).get("DATABASE_URL", "")
database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
parsed = urlsplit(database_url)
if parsed.scheme not in {"postgres", "postgresql"} or not parsed.path.strip("/"):
	raise SystemExit("DATABASE_URL doit désigner une base PostgreSQL.")

pg_dump = shutil.which("pg_dump")
if not pg_dump:
	raise SystemExit("pg_dump introuvable; ajouter le dossier bin PostgreSQL au PATH.")

environment = os.environ.copy()
environment.pop("PGPASSWORD", None)
environment.update({
	"PGHOST": parsed.hostname or "localhost",
	"PGPORT": str(parsed.port or 5432),
	"PGDATABASE": unquote(parsed.path.lstrip("/")),
	"PGAPPNAME": "veloville-backup",
})
if parsed.username:
	environment["PGUSER"] = unquote(parsed.username)
if parsed.password is not None:
	environment["PGPASSWORD"] = unquote(parsed.password)
for parameter, variable in {
	"sslmode": "PGSSLMODE",
	"connect_timeout": "PGCONNECT_TIMEOUT",
	"application_name": "PGAPPNAME",
}.items():
	if parameter in parse_qs(parsed.query):
		environment[variable] = parse_qs(parsed.query)[parameter][0]

try:
	subprocess.run(
		[pg_dump, "--format=custom", "--no-owner", "--no-acl", "--file", str(backup_file)],
		env=environment,
		check=True,
	)
except (OSError, subprocess.CalledProcessError) as error:
	backup_file.unlink(missing_ok=True)
	raise SystemExit(f"Échec de pg_dump : {error}") from None

if not backup_file.is_file() or backup_file.stat().st_size == 0:
	backup_file.unlink(missing_ok=True)
	raise SystemExit("pg_dump n'a pas produit de fichier de sauvegarde valide.")
print(f"Sauvegarde créée : {backup_file}")
PY
