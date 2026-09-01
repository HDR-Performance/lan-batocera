#!/bin/bash
set -euo pipefail

if [ "$(id -u)" != "0" ]; then echo "Run this uninstaller as root." >&2; exit 1; fi

batocera-services stop emulatorjs_lan 2>/dev/null || true
batocera-services stop filebrowser_quantum 2>/dev/null || true
batocera-services stop lan_batocera_mdns 2>/dev/null || true
batocera-services disable emulatorjs_lan 2>/dev/null || true
batocera-services disable filebrowser_quantum 2>/dev/null || true
batocera-services disable lan_batocera_mdns 2>/dev/null || true
rm -f /userdata/system/services/emulatorjs_lan
rm -f /userdata/system/services/filebrowser_quantum
rm -f /userdata/system/services/lan_batocera_mdns
rm -rf /userdata/system/emulatorjs-lan

echo "Services and arcade files removed."
echo "FileBrowser data remains in /userdata/system/filebrowser-quantum for recovery."
echo "ROMs, BIOS files, saves, and screenshots were not touched."
