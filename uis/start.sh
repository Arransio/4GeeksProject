#!/bin/sh
# Arranca las dos aplicaciones Next.js de /uis en puertos distintos:
#   website   -> 3000
#   backoffice -> 3001
set -eu

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEBSITE_PORT="${WEBSITE_PORT:-3000}"
BACKOFFICE_PORT="${BACKOFFICE_PORT:-3001}"

echo "[start.sh] Next.js website en el puerto ${WEBSITE_PORT}"
(cd "${APP_ROOT}/website" && exec ./node_modules/.bin/next start -p "${WEBSITE_PORT}") &
WEB_PID=$!

echo "[start.sh] Next.js backoffice en el puerto ${BACKOFFICE_PORT}"
(cd "${APP_ROOT}/backoffice" && exec ./node_modules/.bin/next start -p "${BACKOFFICE_PORT}") &
BACK_PID=$!

term() {
  trap - INT TERM
  kill "${WEB_PID}" "${BACK_PID}" 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap term INT TERM

# Si una de las dos aplicaciones cae, paramos la otra y salimos con su codigo.
wait "${WEB_PID}" || STATUS=$?
kill "${BACK_PID}" 2>/dev/null || true
wait 2>/dev/null || true
exit "${STATUS:-0}"