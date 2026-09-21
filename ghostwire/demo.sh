#!/bin/bash
# GHOSTWIRE demo: two live app instances over loopback, exchanging a real
# encrypted GW1 session while screenshots are captured under Xvfb.
set -u
cd "$(dirname "$0")"
mkdir -p shots
rm -f shots/*.png
export KIVY_NO_ARGS=1 KIVY_LOG_LEVEL=warning

XVFB() { xvfb-run -a -s "-screen 0 460x780x24" "$@"; }

echo "[demo] launching SERVER node..."
XVFB env GW_DEMO=server python3 main.py > /tmp/gw_server.log 2>&1 &
SERVER_PID=$!
sleep 5

echo "[demo] launching CLIENT operative..."
XVFB env GW_DEMO=client python3 main.py > /tmp/gw_client.log 2>&1
CLIENT_EXIT=$?

wait "$SERVER_PID"
echo "[demo] client exit=$CLIENT_EXIT"
echo "[demo] screenshots:"
ls -la shots/
