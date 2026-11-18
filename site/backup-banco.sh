#!/usr/bin/env bash
# Uso interno do deploy. MYSQL_PWD chega pelo ambiente; nunca por argumento.
set -euo pipefail
umask 077
[[ $# == 6 ]] || { echo 'Argumentos de backup inválidos' >&2; exit 1; }
HOST=$1 PORTA=$2 USUARIO=$3 BANCO=$4 DESTINO=$5 MODO=$6
[[ "$PORTA" =~ ^[0-9]+$ && "$PORTA" -gt 0 && "$PORTA" -le 65535 ]] || exit 1
[[ "$MODO" == atualizar || "$MODO" == instalar ]] || exit 1
CLIENTE=${MYSQL_CLIENT_BIN:-$(command -v mariadb || command -v mysql)}
DUMP=${MYSQL_DUMP_BIN:-$(command -v mariadb-dump || command -v mysqldump)}
ARGS=(--host="$HOST" --port="$PORTA" --user="$USUARIO")
TABELAS=$("$CLIENTE" "${ARGS[@]}" --database="$BANCO" --batch --skip-column-names \
  --execute="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'")
[[ "$TABELAS" =~ ^[0-9]+$ ]] || exit 1
if [[ "$TABELAS" == 0 && "$MODO" != instalar ]]; then
  echo 'Banco vazio: backup de atualização recusado' >&2; exit 1
fi
TEMPORARIO=$(mktemp "${DESTINO}.parcial.XXXXXX")
trap 'rm -f -- "$TEMPORARIO"' EXIT
"$DUMP" "${ARGS[@]}" --single-transaction --no-tablespaces --default-character-set=utf8mb4 "$BANCO" | gzip > "$TEMPORARIO"
gzip -t "$TEMPORARIO"
CRIADAS=$(gzip -cd "$TEMPORARIO" | awk '/^CREATE TABLE / {n++} END {print n+0}')
[[ "$CRIADAS" -ge "$TABELAS" ]] || { echo 'Backup incompleto' >&2; exit 1; }
mv -- "$TEMPORARIO" "$DESTINO"
