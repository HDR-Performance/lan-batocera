#!/bin/bash
set -euo pipefail

APP_ROOT=/userdata/system/batocera-lan-arcade
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
install -m 0644 "$APP_ROOT/web/index.html" "$ARCADE_ROOT/web/index.html"
install -m 0644 "$APP_ROOT/web/play.html" "$ARCADE_ROOT/web/play.html"
install -m 0755 "$APP_ROOT/services/emulatorjs_lan" "$SERVICE_ROOT/emulatorjs_lan"
install -m 0755 "$APP_ROOT/services/filebrowser_quantum" "$SERVICE_ROOT/filebrowser_quantum"

if [ ! -x "$FB_ROOT/filebrowser" ]; then
  echo "Downloading FileBrowser Quantum ${FB_VERSION}..."
  curl -fL "$FB_URL" -o "$FB_ROOT/filebrowser.download"
  chmod 0755 "$FB_ROOT/filebrowser.download"
  mv "$FB_ROOT/filebrowser.download" "$FB_ROOT/filebrowser"
fi

if [ ! -f "$FB_ROOT/config.yaml" ]; then
  install -m 0600 "$APP_ROOT/templates/filebrowser-config.yaml" "$FB_ROOT/config.yaml"
fi

if [ ! -f "$FB_ROOT/filebrowser.db" ]; then
  cd "$FB_ROOT"
  FILEBROWSER_CONFIG="$FB_ROOT/config.yaml" "$FB_ROOT/filebrowser" set user -c "$FB_ROOT/config.yaml" -u Batocera,Batocera -a
  chmod 0600 "$FB_ROOT/config.yaml"
  printf '\nFile manager first login\nUsername: Batocera\nPassword: Batocera\nChange both in Settings after signing in.\n\n'
else
  echo "Keeping the existing file-manager account and password."
fi

batocera-services enable emulatorjs_lan
batocera-services enable filebrowser_quantum
batocera-services restart emulatorjs_lan || "$SERVICE_ROOT/emulatorjs_lan" start
batocera-services restart filebrowser_quantum || "$SERVICE_ROOT/filebrowser_quantum" start

IP_ADDRESS="$(hostname -I | awk '{print $1}')"
echo "Arcade:      http://${IP_ADDRESS}:8080"
echo "File manager: http://${IP_ADDRESS}:8081"
echo "Installation complete."
