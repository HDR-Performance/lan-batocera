#!/bin/bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
ARCADE_ROOT=/userdata/system/emulatorjs-lan
FB_ROOT=/userdata/system/filebrowser-quantum
SERVICE_ROOT=/userdata/system/services
FB_VERSION=v1.5.3-stable
FB_URL="https://github.com/gtsteffaniak/filebrowser/releases/download/${FB_VERSION}/linux-arm64-filebrowser"

if [ "$(id -u)" != "0" ]; then echo "Run this installer as root." >&2; exit 1; fi
if [ ! -d /userdata ] || [ ! -x /usr/bin/batocera-services ]; then echo "Batocera v38+ is required." >&2; exit 1; fi
if [ "$(uname -m)" != "aarch64" ]; then echo "This release currently supports aarch64 Batocera devices only." >&2; exit 1; fi

mkdir -p "$ARCADE_ROOT/web" "$FB_ROOT/cache" "$SERVICE_ROOT" /userdata/system/logs
install -m 0755 "$APP_ROOT/src/server.py" "$ARCADE_ROOT/server.py"
install -m 0644 "$APP_ROOT/VERSION" "$ARCADE_ROOT/VERSION"
install -m 0755 "$APP_ROOT/src/upload_proxy.py" "$FB_ROOT/upload_proxy.py"
install -m 0644 "$APP_ROOT/web/index.html" "$ARCADE_ROOT/web/index.html"
install -m 0644 "$APP_ROOT/web/play.html" "$ARCADE_ROOT/web/play.html"
install -m 0644 "$APP_ROOT/web/controller-presets.js" "$ARCADE_ROOT/web/controller-presets.js"
install -m 0644 "$APP_ROOT/web/themes.js" "$ARCADE_ROOT/web/themes.js"
install -m 0755 "$APP_ROOT/services/emulatorjs_lan" "$SERVICE_ROOT/emulatorjs_lan"
install -m 0755 "$APP_ROOT/services/filebrowser_quantum" "$SERVICE_ROOT/filebrowser_quantum"
install -m 0755 "$APP_ROOT/services/lan_batocera_mdns" "$SERVICE_ROOT/lan_batocera_mdns"

if [ ! -x "$FB_ROOT/filebrowser" ]; then
  echo "Downloading FileBrowser Quantum ${FB_VERSION}..."
  curl -fL "$FB_URL" -o "$FB_ROOT/filebrowser.download"
  chmod 0755 "$FB_ROOT/filebrowser.download"
  mv "$FB_ROOT/filebrowser.download" "$FB_ROOT/filebrowser"
fi

NEW_ACCOUNT=0
if [ ! -f "$FB_ROOT/config.yaml" ]; then
  install -m 0600 "$APP_ROOT/templates/filebrowser-config.yaml" "$FB_ROOT/config.yaml"
fi

if [ ! -f "$FB_ROOT/filebrowser.db" ]; then
  NEW_ACCOUNT=1
else
  echo "Keeping the existing file-manager account and password."
fi

batocera-services enable emulatorjs_lan
batocera-services enable filebrowser_quantum
batocera-services enable lan_batocera_mdns
batocera-services restart emulatorjs_lan || "$SERVICE_ROOT/emulatorjs_lan" start
batocera-services restart filebrowser_quantum || "$SERVICE_ROOT/filebrowser_quantum" start
batocera-services restart lan_batocera_mdns || "$SERVICE_ROOT/lan_batocera_mdns" start

if [ "$NEW_ACCOUNT" = "1" ]; then
  printf '\nFile manager first login\nUsername: Batocera\nPassword: Batocera\nChange both in Profile -> Security after signing in.\n\n'
fi

IP_ADDRESS="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}')"
echo "Arcade:      http://${IP_ADDRESS}:8080"
echo "File manager: http://${IP_ADDRESS}:8081"
echo "Friendly arcade address: http://batocera.local:8080"
echo "Friendly ROM address:    http://batoceraroms.local:8081"
echo "LAN Batocera version:     $(cat "$APP_ROOT/VERSION")"
echo "Installation complete."
