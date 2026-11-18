#!/usr/bin/env bash
# Publica o site institucional em nexus.figueiredo.dev. Uso: ./site-institucional/deploy.sh
#
# Precisa no .env da raiz (ou no ambiente): HOSTINGER_USER, HOSTINGER_HOST, HOSTINGER_PORT e HOSTINGER_SSH_KEY,
# os mesmos do site/deploy.sh. Node 20.19+ ou 22.12+ (exigência do Vite 8).
# Antes de trocar, guarda o que está no ar em ~/backups-nexus/ no servidor (fica com os 10 últimos).
# Se o backup falhar, nada é publicado.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(dirname "$AQUI")"
if [[ -f "$RAIZ/.env" ]]; then set -a; source "$RAIZ/.env"; set +a; fi

DOMINIO="${NEXUS_DOMINIO:-nexus.figueiredo.dev}"
SSH="ssh -i ${HOSTINGER_SSH_KEY/#\~/$HOME} -p $HOSTINGER_PORT -o BatchMode=yes"
ALVO="$HOSTINGER_USER@$HOSTINGER_HOST"
DIR="/home/$HOSTINGER_USER/domains/$DOMINIO"

cd "$AQUI"
npm ci --ignore-scripts --no-audit --no-fund     # versões do package-lock, sem scripts de instalação
npm run build

CARIMBO="$(date +%Y%m%d-%H%M%S)"
$SSH "$ALVO" "umask 077; mkdir -p ~/backups-nexus; test -d $DIR/public_html && tar czf ~/backups-nexus/$CARIMBO.tar.gz -C $DIR public_html"
$SSH "$ALVO" "cd ~/backups-nexus && ls -1t | tail -n +11 | xargs -r rm -f"
echo "backup ok: ~/backups-nexus/$CARIMBO.tar.gz"

rsync -az --delete -e "$SSH" dist/ "$ALVO:$DIR/public_html/"
echo "ok → https://$DOMINIO"
