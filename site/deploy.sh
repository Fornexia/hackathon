#!/usr/bin/env bash
# Sobe o site para fornexia.figueiredo.dev em ~10s. Uso: ./site/deploy.sh [--setup]
#   --setup  cria/atualiza as tabelas, os planos e o admin (rode na primeira vez e após mudar o schema)
#
# Precisa no .env (ou no ambiente, como no GitHub Actions): HOSTINGER_*, SITE, DB_HOST, DB_NAME, DB_USER,
# DB_PASS, WORKER_KEY (24+ caracteres), e ADMIN_EMAIL e ADMIN_SENHA para o --setup. DB_PORT é opcional.
# Antes de publicar, guarda os arquivos e o banco em ~/backups-fornexia/ no servidor (fica com os 10 últimos).
# Se o backup falhar, nada é publicado.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$RAIZ/.env" ]]; then set -a; source "$RAIZ/.env"; set +a; fi

: "${WORKER_KEY:?defina WORKER_KEY no .env (mínimo 24 caracteres)}"
if [[ ${#WORKER_KEY} -lt 24 ]]; then echo "WORKER_KEY precisa ter pelo menos 24 caracteres" >&2; exit 1; fi

SSH="ssh -i ${HOSTINGER_SSH_KEY/#\~/$HOME} -p $HOSTINGER_PORT -o BatchMode=yes"
ALVO="$HOSTINGER_USER@$HOSTINGER_HOST"
DOMINIO_DIR="/home/$HOSTINGER_USER/domains/$SITE"

# Backup antes de tudo: arquivos do domínio e o banco. A senha do banco vai pela entrada padrão, nunca na linha de comando.
CARIMBO="$(date +%Y%m%d-%H%M%S)"
$SSH "$ALVO" "umask 077; mkdir -p ~/backups-fornexia; if [ -d $DOMINIO_DIR ]; then tar czf ~/backups-fornexia/$CARIMBO-arquivos.tar.gz -C $DOMINIO_DIR .; fi"
printf '%s' "$DB_PASS" | $SSH "$ALVO" "umask 077; MYSQL_PWD=\$(cat) mysqldump --no-tablespaces -h $(printf '%q' "$DB_HOST") -u $(printf '%q' "$DB_USER") $(printf '%q' "$DB_NAME") | gzip > ~/backups-fornexia/$CARIMBO-banco.sql.gz && test \$(zcat ~/backups-fornexia/$CARIMBO-banco.sql.gz | grep -c 'CREATE TABLE') -gt 0"
$SSH "$ALVO" "cd ~/backups-fornexia && ls -1t | tail -n +21 | xargs -r rm -f"
echo "backup ok: ~/backups-fornexia/$CARIMBO-*"

# Texto seguro dentro de uma string PHP entre aspas simples: escapa a barra invertida e a aspa simples.
# Sem isto, uma senha com ' quebrava o arquivo de configuração (ou injetava código nele).
php_str() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/\\\\'/g"; }

# Config com segredos: gerada aqui, gravada fora do public_html, nunca versionada.
$SSH "$ALVO" "umask 077; cat > $DOMINIO_DIR/hackathon-config.php" <<PHP
<?php
const AMBIENTE = 'prod';
const DB_HOST = '$(php_str "$DB_HOST")';
$( [[ -n "${DB_PORT:-}" ]] && echo "const DB_PORT = $((DB_PORT));" )
const DB_NAME = '$(php_str "$DB_NAME")';
const DB_USER = '$(php_str "$DB_USER")';
const DB_PASS = '$(php_str "$DB_PASS")';
const WORKER_KEY = '$(php_str "$WORKER_KEY")';
PHP

rsync -az --delete -e "$SSH" "$RAIZ/site/public_html/" "$ALVO:$DOMINIO_DIR/public_html/"
rsync -az -e "$SSH" "$RAIZ/site/setup.php" "$ALVO:$DOMINIO_DIR/setup.php"
[[ -f "$RAIZ/dados/painel.json" ]] && rsync -az --chmod=F600 -e "$SSH" "$RAIZ/dados/painel.json" "$ALVO:$DOMINIO_DIR/painel.json"
$SSH "$ALVO" "rm -f $DOMINIO_DIR/public_html/default.php"

if [[ "${1:-}" == "--setup" ]]; then
  # printf %q protege o texto para o shell do servidor (aspas, espaços, $ e outros).
  $SSH "$ALVO" "php $DOMINIO_DIR/setup.php $(printf '%q' "$ADMIN_EMAIL") Admin $(printf '%q' "$ADMIN_SENHA")"
fi
echo "ok → https://$SITE"
