#!/bin/bash
set -euo pipefail

LAN_BATOCERA_VERSION="1.7.1"
REPOSITORY="HDR-Performance/lan-batocera"
ARCHIVE_URL="https://github.com/${REPOSITORY}/archive/refs/tags/v${LAN_BATOCERA_VERSION}.tar.gz"
TEMPORARY_DIRECTORY="$(mktemp -d /tmp/lan-batocera-standalone.XXXXXX)"
ARCHIVE_PATH="${TEMPORARY_DIRECTORY}/lan-batocera.tar.gz"
SOURCE_DIRECTORY="${TEMPORARY_DIRECTORY}/source"

cleanup() {
  case "$TEMPORARY_DIRECTORY" in
    /tmp/lan-batocera-standalone.*) ;;
    *) echo "Refusing to remove an unexpected temporary path." >&2; return ;;
  esac
  rm -rf -- "$TEMPORARY_DIRECTORY"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

trap cleanup EXIT

if [ "$(id -u)" != "0" ]; then
  echo "Run this installer as root on an existing Batocera system." >&2
  exit 1
fi

if [ ! -d /userdata ] || [ ! -x /usr/bin/batocera-services ]; then
  echo "This standalone installer requires an existing Batocera installation." >&2
  exit 1
fi

require_command curl
require_command tar

mkdir -p "$SOURCE_DIRECTORY"
echo "Downloading LAN Batocera v${LAN_BATOCERA_VERSION}..."
curl -fL "$ARCHIVE_URL" -o "$ARCHIVE_PATH"
tar -xzf "$ARCHIVE_PATH" -C "$SOURCE_DIRECTORY" --strip-components=1

if [ "$(cat "$SOURCE_DIRECTORY/VERSION")" != "$LAN_BATOCERA_VERSION" ]; then
  echo "Downloaded release version does not match the installer." >&2
  exit 1
fi

chmod +x "$SOURCE_DIRECTORY/install.sh"
"$SOURCE_DIRECTORY/install.sh"
