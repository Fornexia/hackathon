#!/usr/bin/env bash
# Instala o monitor na conta Linux atual, depois de publicar a rota do site.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
[[ -x "$RAIZ/.venv/bin/python" ]] || { echo 'Prepare a .venv do projeto antes de instalar.' >&2; exit 1; }
[[ -f "$RAIZ/.env" ]] || { echo 'Configure .env com WORKER_KEY e SMTP do site antes de instalar.' >&2; exit 1; }
DESTINO="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$DESTINO"
cat > "$DESTINO/fornexia-alertas.service" <<UNIT
[Unit]
Description=FornexIA: monitora fornecedores acompanhados no site e envia alertas por e-mail
After=network-online.target

[Service]
WorkingDirectory=$RAIZ
ExecStart="$RAIZ/.venv/bin/python" "$RAIZ/alertas/ponte_site.py"
Environment=PYTHONUNBUFFERED=1
Environment=ALERTAS_ENVIO=smtp
UMask=0077
Restart=on-failure
RestartSec=15

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now fornexia-alertas.service
systemctl --user is-active fornexia-alertas.service
