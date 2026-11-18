#!/usr/bin/env bash
# Sobe o site para fornexia.figueiredo.dev em ~10s. Uso: ./site/deploy.sh [--setup]
#   --setup  instalação inicial e provisionamento explícito do admin; atualizações usam migração aditiva
#
# Precisa no .env (ou no ambiente, como no GitHub Actions): HOSTINGER_*, SITE, DB_HOST, DB_NAME, DB_USER,
# DB_PASS, WORKER_KEY (24+ caracteres), e ADMIN_EMAIL e ADMIN_SENHA para o --setup. DB_PORT é opcional.
# Antes de publicar, guarda os arquivos e o banco em ~/backups-fornexia/ no servidor (fica com os 10 últimos).
# Se o backup falhar, nada é publicado.
set -euo pipefail
MODO=atualizar
if [[ "${1:-}" == --setup && $# == 1 ]]; then MODO=instalar
elif [[ $# != 0 ]]; then echo 'Uso: deploy.sh [--setup]' >&2; exit 1; fi
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$RAIZ/.env" ]]; then set -a; source "$RAIZ/.env"; set +a; fi

: "${WORKER_KEY:?defina WORKER_KEY no .env (mínimo 24 caracteres)}"
if [[ ${#WORKER_KEY} -lt 24 ]]; then echo "WORKER_KEY precisa ter pelo menos 24 caracteres" >&2; exit 1; fi
# O cadastro novo depende do correio; falhar antes de publicar evita contas sem caminho de verificação.
for VAR_AUTH in APP_URL SMTP_HOST SMTP_USER SMTP_PASS MAIL_FROM AUTH_MAIL_KEY; do
  if [[ -z "${!VAR_AUTH:-}" ]]; then echo "defina $VAR_AUTH antes de publicar o login público" >&2; exit 1; fi
done
if [[ "$APP_URL" != https://* || ! -f "$RAIZ/site/vendor/autoload.php" ]]; then
  echo "APP_URL deve usar HTTPS; execute composer install --no-dev em site/ antes de publicar" >&2; exit 1
fi

# Opcionais do login: GOOGLE_CLIENT_ID (liga o botão "Entrar com Google") e TRUSTED_PROXIES (IPs de proxies confiáveis, separados por vírgula).
# Formato conferido antes de publicar: um erro de digitação deixaria o botão sem funcionar ou o limite de tentativas errado.
if [[ -n "${GOOGLE_CLIENT_ID:-}" && ! "$GOOGLE_CLIENT_ID" =~ ^[0-9]+-[A-Za-z0-9_]+\.apps\.googleusercontent\.com$ ]]; then
  echo "GOOGLE_CLIENT_ID fora do formato (NUMEROS-texto.apps.googleusercontent.com); confira no Google Cloud Console" >&2; exit 1
fi
if [[ -n "${TRUSTED_PROXIES:-}" && ! "$TRUSTED_PROXIES" =~ ^[0-9A-Fa-f:.,\ ]+$ ]]; then
  echo "TRUSTED_PROXIES deve ter só endereços IP separados por vírgula" >&2; exit 1
fi

SSH="ssh -i ${HOSTINGER_SSH_KEY/#\~/$HOME} -p $HOSTINGER_PORT -o BatchMode=yes"
ALVO="$HOSTINGER_USER@$HOSTINGER_HOST"
DOMINIO_DIR="/home/$HOSTINGER_USER/domains/$SITE"

# Backup antes de tudo: arquivos do domínio e o banco. A senha do banco vai pela entrada padrão, nunca na linha de comando.
CARIMBO="$(date +%Y%m%d-%H%M%S)"
$SSH "$ALVO" "set -eu; umask 077; mkdir -p ~/backups-fornexia; if [ -d $DOMINIO_DIR ]; then tar czf ~/backups-fornexia/$CARIMBO-arquivos.tar.gz -C $DOMINIO_DIR .; fi"
{
  printf 'export MYSQL_PWD=%q\n' "$DB_PASS"
  printf 'set -- %q %q %q %q "$HOME/backups-fornexia/%s-banco.sql.gz" %q\n' "$DB_HOST" "${DB_PORT:-3306}" "$DB_USER" "$DB_NAME" "$CARIMBO" "$MODO"
  cat "$RAIZ/site/backup-banco.sh"
} | $SSH "$ALVO" 'bash -s'
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
const APP_URL = '$(php_str "$APP_URL")';
const SMTP_HOST = '$(php_str "$SMTP_HOST")';
const SMTP_PORT = '$(php_str "${SMTP_PORT:-587}")';
const SMTP_SECURITY = '$(php_str "${SMTP_SECURITY:-tls}")';
const SMTP_USER = '$(php_str "$SMTP_USER")';
const SMTP_PASS = '$(php_str "$SMTP_PASS")';
const MAIL_FROM = '$(php_str "$MAIL_FROM")';
const MAIL_FROM_NAME = '$(php_str "${MAIL_FROM_NAME:-FORNEX}")';
const AUTH_MAIL_KEY = '$(php_str "$AUTH_MAIL_KEY")';
$( [[ -n "${GOOGLE_CLIENT_ID:-}" ]] && echo "const GOOGLE_CLIENT_ID = '$(php_str "$GOOGLE_CLIENT_ID")';" )
$( [[ -n "${TRUSTED_PROXIES:-}" ]] && echo "const TRUSTED_PROXIES = '$(php_str "$TRUSTED_PROXIES")';" )
PHP

# Dependências e migração antes de trocar a API pública. O setup completo não é necessário para atualizar contas.
rsync -az -e "$SSH" "$RAIZ/site/config.php" "$RAIZ/site/migrar-autenticacao.php" "$RAIZ/site/migrar-tokens.php" "$RAIZ/site/enviar-emails.php" "$RAIZ/site/setup.php" "$RAIZ/site/composer.json" "$RAIZ/site/composer.lock" "$ALVO:$DOMINIO_DIR/"
rsync -az --exclude=.git -e "$SSH" "$RAIZ/site/vendor/" "$ALVO:$DOMINIO_DIR/vendor/"
if [[ "${1:-}" == "--setup" ]]; then
  # Somente instalação/provisionamento explícito; a migração comum não redefine o admin.
  $SSH "$ALVO" "php $DOMINIO_DIR/setup.php $(printf '%q' "$ADMIN_EMAIL") Admin $(printf '%q' "$ADMIN_SENHA")"
fi
$SSH "$ALVO" "php $DOMINIO_DIR/migrar-autenticacao.php && php $DOMINIO_DIR/migrar-tokens.php"
rsync -az --delete -e "$SSH" "$RAIZ/site/public_html/" "$ALVO:$DOMINIO_DIR/public_html/"
[[ -f "$RAIZ/dados/painel.json" ]] && rsync -az --chmod=F600 -e "$SSH" "$RAIZ/dados/painel.json" "$ALVO:$DOMINIO_DIR/painel.json"
$SSH "$ALVO" "rm -f $DOMINIO_DIR/public_html/default.php"

echo "ok → https://$SITE"
