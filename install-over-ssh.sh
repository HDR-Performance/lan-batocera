#!/bin/sh
set -eu

LAN_BATOCERA_VERSION="1.8.2"
DEVICE_HOST="${1:-batocera.local}"
SSH_USER="${SSH_USER:-root}"
INSTALLER_URL="https://raw.githubusercontent.com/HDR-Performance/lan-batocera/v${LAN_BATOCERA_VERSION}/standalone-install.sh"
REMOTE_INSTALLER_PATH="/tmp/lan-batocera-install.sh"

if ! command -v ssh >/dev/null 2>&1; then
  echo "OpenSSH is required." >&2
  exit 1
fi

case "$DEVICE_HOST" in
  *[!A-Za-z0-9._:-]*)
    echo "The device host contains unsupported characters." >&2
    exit 1
    ;;
esac

echo "Installing LAN Batocera v${LAN_BATOCERA_VERSION} on ${SSH_USER}@${DEVICE_HOST}..."
ssh "${SSH_USER}@${DEVICE_HOST}" \
  "curl -fL '${INSTALLER_URL}' -o '${REMOTE_INSTALLER_PATH}' && chmod 0700 '${REMOTE_INSTALLER_PATH}' && '${REMOTE_INSTALLER_PATH}'"
echo "LAN Batocera v${LAN_BATOCERA_VERSION} installed successfully."
