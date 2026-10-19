#!/usr/bin/env bash
# Registra el webhook de Telegram apuntando a la URL pública de Render
# (el registro queda en <base>/telegram).
#
# Uso:
#   scripts/set_webhook_url.sh https://<servicio>.onrender.com
#
# Por qué existe: el token del bot viaja DENTRO de la URL de la llamada a la
# Bot API (api.telegram.org/bot<token>/...). Si se tipea a mano, queda en
# ~/.bash_history; este script lee el token y el secret desde .env y los pasa
# por variables, así que nunca se escriben en el shell ni se imprimen.
#
# Valida la URL argumento, llama a setWebhook (con el mismo parámetro que
# registra scripts/run_webhook_tunnel.sh) y después muestra getWebhookInfo
# para confirmar que Telegram aceptó el registro.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="$ROOT/venv/bin/python"
ENV_FILE="$ROOT/.env"
API_BASE="https://api.telegram.org"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Lee una variable del .env sin imprimirla (dotenv resuelve comillas y espacios).
env_val() {
    [ -f "$ENV_FILE" ] || return 1
    "$PYTHON" -c 'import sys; from dotenv import dotenv_values
print(dotenv_values(sys.argv[1]).get(sys.argv[2]) or "")' "$ENV_FILE" "$1"
}

[ -x "$PYTHON" ] || die "No se encontró $PYTHON (¿falta el venv?)"

[ $# -eq 1 ] || die "Uso: scripts/set_webhook_url.sh https://<servicio>.onrender.com"
BASE="${1%/}"
[[ "$BASE" =~ ^https?://[^/[:space:]]+ ]] \
    || die "el argumento debe ser una URL http(s), p. ej. https://communitylab-webhook.onrender.com"

token="$(env_val TELEGRAM_BOT_TOKEN || true)"
[ -n "$token" ] || die "TELEGRAM_BOT_TOKEN no está en .env"
secret="$(env_val TELEGRAM_WEBHOOK_SECRET || true)"
[ -n "$secret" ] \
    || die "TELEGRAM_WEBHOOK_SECRET no está en .env (sin él /telegram responde 503)"

url_webhook="${BASE}/telegram"
log "setWebhook: registrando ${url_webhook} (token enmascarado: ****)"
# Mismo setWebhook que scripts/run_webhook_tunnel.sh: url + secret_token.
respuesta="$(curl -s -m 20 -X POST "$API_BASE/bot${token}/setWebhook" \
    --data-urlencode "url=${url_webhook}" \
    --data-urlencode "secret_token=${secret}")" \
    || die "no se pudo contactar a api.telegram.org (sin red o timeout)"
if ! printf '%s' "$respuesta" | grep -q '"ok":true'; then
    die "setWebhook falló: $respuesta"
fi
log "setWebhook: OK"

info="$(curl -s -m 20 "$API_BASE/bot${token}/getWebhookInfo")" \
    || die "no se pudo contactar a api.telegram.org (sin red o timeout)"
printf '%s' "$info" | "$PYTHON" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except ValueError:
    print("getWebhookInfo: respuesta no interpretable")
    raise SystemExit(1)
if not data.get("ok"):
    print("getWebhookInfo: la API respondió ok=false")
    raise SystemExit(1)
result = data.get("result") or {}
print("url                 :", result.get("url") or "-")
print("pending_update_count:", result.get("pending_update_count", 0))
print("last_error_message  :", result.get("last_error_message") or "-")
'

log ""
log "Listo. Verificación manual:"
log "  curl ${BASE}/health"
