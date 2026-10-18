#!/usr/bin/env bash
# Relanza el webhook de Telegram + túnel público de Cloudflare y vuelve a
# registrar setWebhook con la URL nueva.
#
# Uso:
#   scripts/run_webhook_tunnel.sh start    # server + túnel + setWebhook (default)
#   scripts/run_webhook_tunnel.sh status   # qué está corriendo y qué ve Telegram
#   scripts/run_webhook_tunnel.sh stop     # apaga túnel y server
#
# Variables opcionales: WEBHOOK_PORT (8765) y WEBHOOK_BACKEND (rule_based).
#
# Por qué existe: el túnel rápido de Cloudflare genera una URL distinta en cada
# arranque y Telegram exige HTTPS con un certificado válido (no acepta
# autofirmados), así que cada relanzado requiere repetir setWebhook con la URL
# nueva. Este script hace las dos cosas juntas para que no haya que hacerlo a
# mano ni adivinar la URL en el log.
#
# El polling queda fuera de este script a propósito: con el webhook activo, el
# bot se atiende por un único camino (POST /telegram).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${WEBHOOK_PORT:-8765}"
BACKEND="${WEBHOOK_BACKEND:-rule_based}"
PYTHON="$ROOT/venv/bin/python"
CLOUDFLARED="${CLOUDFLARED:-$HOME/.local/bin/cloudflared}"
ENV_FILE="$ROOT/.env"
LOGDIR="${TMPDIR:-/tmp}/communitylab"
WEBHOOK_LOG="$LOGDIR/webhook.log"
TUNNEL_LOG="$LOGDIR/tunnel.log"
API_BASE="https://api.telegram.org"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Lee una variable del .env sin imprimirla (dotenv resuelve comillas y espacios).
env_val() {
    [ -f "$ENV_FILE" ] || return 1
    "$PYTHON" -c 'import sys; from dotenv import dotenv_values
print(dotenv_values(sys.argv[1]).get(sys.argv[2]) or "")' "$ENV_FILE" "$1"
}

# PID escuchando en el puerto del webhook (evita pkill -f, que puede matar el
# propio proceso si su línea de comando contiene el patrón).
pid_en_puerto() {
    ss -tlnp 2>/dev/null | grep ":$PORT " | grep -o 'pid=[0-9]*' \
        | head -1 | cut -d= -f2
}

pid_tunel() { pgrep -f "cloudflared tunnel --url" | head -1; }

salud() {
    curl -s -m 5 "http://127.0.0.1:$PORT/health" 2>/dev/null || true
}

info_webhook() {
    local token
    token="$(env_val TELEGRAM_BOT_TOKEN)"
    [ -n "$token" ] || die "TELEGRAM_BOT_TOKEN no está en .env"
    curl -s -m 15 "$API_BASE/bot${token}/getWebhookInfo"
}

server_listo() {
    # Espera a que el server responda en vez de asumir que arrancó.
    local i
    for i in $(seq 1 20); do
        [ -n "$(salud)" ] && return 0
        sleep 1
    done
    return 1
}

url_en_log() {
    grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null \
        | head -1 || true
}

tunel_url() {
    local url i pid
    pid="$(pid_tunel)"
    if [ -n "$pid" ]; then
        # Ya hay un túnel: reutilizamos su URL en vez de levantar otro.
        url="$(url_en_log)"
        [ -n "$url" ] && { printf '%s' "$url"; return 0; }
        log "tunel  : hay un túnel (pid $pid) sin URL legible; lo reinicio" >&2
        kill "$pid" 2>/dev/null || true
        sleep 2
    fi
    : > "$TUNNEL_LOG"   # si no se limpia, queda la URL del arranque anterior
    nohup "$CLOUDFLARED" tunnel --url "http://127.0.0.1:$PORT" \
        > "$TUNNEL_LOG" 2>&1 &
    for i in $(seq 1 45); do
        url="$(url_en_log)"
        if [ -n "$url" ]; then
            printf '%s' "$url"
            return 0
        fi
        sleep 1
    done
    return 1
}

# El túnel publica la URL antes de aceptar conexiones reales; Telegram resuelve
# el host al validar setWebhook, así que hay que esperar a que responda.
tunel_listo() {
    local url="$1" i
    for i in $(seq 1 20); do
        if curl -s -f -m 8 -o /dev/null "$url/health"; then
            return 0
        fi
        sleep 2
    done
    return 1
}

registrar_webhook() {
    local url="$1" token secret respuesta intento
    token="$(env_val TELEGRAM_BOT_TOKEN)"
    secret="$(env_val TELEGRAM_WEBHOOK_SECRET)"
    [ -n "$token" ] || die "TELEGRAM_BOT_TOKEN no está en .env"
    [ -n "$secret" ] \
        || die "TELEGRAM_WEBHOOK_SECRET no está en .env (sin él /telegram responde 503)"

    for intento in 1 2 3; do
        respuesta="$(curl -s -m 20 -X POST "$API_BASE/bot${token}/setWebhook" \
            --data-urlencode "url=${url}/telegram" \
            --data-urlencode "secret_token=${secret}")"
        if printf '%s' "$respuesta" | grep -q '"ok":true'; then
            return 0
        fi
        log "setWebhook: intento $intento falló: $respuesta" >&2
        sleep 3
    done
    die "setWebhook falló tras 3 intentos: $respuesta
Si el error es 'Failed to resolve host', el hostname recién creado todavía no
llegó al resolver de Telegram: volvé a correr 'stop' y 'start' para generar
otra URL."
}

# El server carga .env al arrancar: si el archivo cambió después, queda con
# valores viejos (token rotado, secret nuevo, backend distinto) y hay que
# reiniciarlo aunque "ya esté corriendo".
server_desactualizado() {
    local pid="$1" et inicio
    et="$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')"
    [ -n "$et" ] || return 1
    [ -f "$ENV_FILE" ] || return 1
    inicio=$(( $(date +%s) - et ))
    [ "$(stat -c %Y "$ENV_FILE")" -gt "$inicio" ]
}

cmd_start() {
    [ -x "$PYTHON" ] || die "No se encontró $PYTHON (¿falta el venv?)"
    [ -x "$CLOUDFLARED" ] || die "No se encontró cloudflared. Instalalo con:
  curl -sL -o ~/.local/bin/cloudflared \\
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x ~/.local/bin/cloudflared"
    mkdir -p "$LOGDIR"

    local pid
    pid="$(pid_en_puerto)"
    if [ -n "$pid" ] && server_desactualizado "$pid"; then
        log "server : .env cambió después del arranque (pid $pid); lo reinicio"
        kill "$pid" 2>/dev/null || true
        sleep 2
        pid=""
    fi

    if [ -n "$pid" ]; then
        log "server : ya corriendo (pid $pid) en el puerto $PORT"
    else
        nohup "$PYTHON" scripts/run_webhook.py --host 127.0.0.1 \
            --port "$PORT" --backend "$BACKEND" > "$WEBHOOK_LOG" 2>&1 &
        server_listo || { tail -5 "$WEBHOOK_LOG" >&2; die "el server no respondió"; }
        log "server : OK (pid $(pid_en_puerto)) en http://127.0.0.1:$PORT"
    fi
    log "salud  : $(salud)"

    local url
    url="$(tunel_url)" || {
        tail -5 "$TUNNEL_LOG" >&2
        die "el túnel no devolvió URL"
    }
    log "tunel  : OK (pid $(pid_tunel))"
    log "url    : $url/telegram"

    tunel_listo "$url" || {
        tail -5 "$TUNNEL_LOG" >&2
        die "el túnel no aceptó conexiones públicas"
    }
    log "tunel  : responde por la URL pública"

    registrar_webhook "$url"
    log "setWebhook: OK"

    log "info   : $(info_webhook)"
    log ""
    log "Listo. Escribile al bot en Telegram (en privado) y debería responder."
    log "Logs: $WEBHOOK_LOG | $TUNNEL_LOG"
    log "Ojo: la URL del túnel rápido cambia en cada arranque; volvé a correr"
    log "     'start' después de reiniciar y setWebhook se repite solo."
}

cmd_status() {
    local pid h info url
    pid="$(pid_en_puerto)"
    h="$(salud)"
    if [ -n "$pid" ]; then
        log "server : pid $pid${h:+ / salud $h}"
    else
        log "server : apagado"
    fi

    pid="$(pid_tunel)"
    if [ -n "$pid" ]; then
        log "tunel  : pid $pid"
    else
        log "tunel  : apagado"
    fi

    url="$(url_en_log)"
    if [ -n "$url" ]; then
        log "url    : $url/telegram"
    elif [ -f "$TUNNEL_LOG" ]; then
        log "url    : sin URL en $TUNNEL_LOG (corré 'start')"
    else
        log "url    : sin log todavía (corré 'start')"
    fi
    if info="$(info_webhook 2>/dev/null)"; then
        log "telegram: $info"
    else
        log "telegram: sin información (falta token o red)"
    fi
}

cmd_stop() {
    local pid
    pid="$(pid_tunel)"
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null && log "tunel  : apagado (pid $pid)"; fi
    pid="$(pid_en_puerto)"
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null && log "server : apagado (pid $pid)"; fi
    log "Telegram sigue apuntando a la URL vieja hasta el próximo 'start'."
}

case "${1:-start}" in
    start)  cmd_start ;;
    status) cmd_status ;;
    stop)   cmd_stop ;;
    *)      die "comando desconocido: $1 (usa start | status | stop)" ;;
esac
