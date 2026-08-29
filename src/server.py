#!/usr/bin/env python3
import json
import mimetypes
import os
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

WEB_ROOT = "/userdata/system/emulatorjs-lan/web"
ROMS_ROOT = "/userdata/roms"
PORT = 8080

SYSTEMS = {
    "nes": ("nes", "Nintendo Entertainment System", "Console", {".nes", ".zip"}),
    "snes": ("snes", "Super Nintendo", "Console", {".sfc", ".smc", ".zip"}),
    "megadrive": ("segaMD", "Sega Genesis / Mega Drive", "Console", {".bin", ".gen", ".md", ".zip"}),
    "sega32x": ("sega32x", "Sega 32X", "Console", {".32x", ".smd", ".bin", ".md", ".zip", ".7z"}),
    "mastersystem": ("segaMS", "Sega Master System", "Console", {".sms", ".zip"}),
    "gamegear": ("segaGG", "Sega Game Gear", "Handheld", {".gg", ".zip"}),
    "gb": ("gb", "Nintendo Game Boy", "Handheld", {".gb", ".zip"}),
    "gbc": ("gb", "Nintendo Game Boy Color", "Handheld", {".gbc", ".zip"}),
    "gba": ("gba", "Nintendo Game Boy Advance", "Handheld", {".gba", ".zip"}),
    "n64": ("n64", "Nintendo 64", "Console", {".n64", ".v64", ".z64", ".zip"}),
    "atari2600": ("atari2600", "Atari 2600", "Console", {".a26", ".bin", ".zip"}),
    "atari7800": ("atari7800", "Atari 7800", "Console", {".a78", ".bin", ".zip"}),
    "lynx": ("lynx", "Atari Lynx", "Handheld", {".lnx", ".zip"}),
    "ngp": ("ngp", "Neo Geo Pocket", "Handheld", {".ngp", ".ngc", ".zip"}),
    "ngpc": ("ngp", "Neo Geo Pocket Color", "Handheld", {".ngp", ".ngc", ".zip"}),
    "wswan": ("ws", "WonderSwan", "Handheld", {".ws", ".wsc", ".zip"}),
    "wswanc": ("ws", "WonderSwan Color", "Handheld", {".ws", ".wsc", ".zip"}),
}


def safe_join(root, relative):
    target = os.path.realpath(os.path.join(root, relative))
    resolved_root = os.path.realpath(root)
    if target != resolved_root and not target.startswith(resolved_root + os.sep):
        raise ValueError("invalid path")
    return target


def games():
    result = []
    for system, (core, system_name, category, extensions) in SYSTEMS.items():
        folder = os.path.join(ROMS_ROOT, system)
        if not os.path.isdir(folder):
            continue
        for base, _, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1].lower() not in extensions:
                    continue
                full = os.path.join(base, filename)
                relative = os.path.relpath(full, ROMS_ROOT).replace(os.sep, "/")
                result.append({"name": os.path.splitext(filename)[0], "system": system,
                               "systemName": system_name, "category": category,
                               "core": core, "path": relative})
    return sorted(result, key=lambda game: (game["category"], game["systemName"],
                                            game["name"].lower()))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/games":
            payload = json.dumps(games()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path.startswith("/roms/"):
            try:
                filename = safe_join(ROMS_ROOT, urllib.parse.unquote(parsed.path[6:]))
                if not os.path.isfile(filename):
                    raise FileNotFoundError
                size = os.path.getsize(filename)
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(size))
                self.end_headers()
                with open(filename, "rb") as source:
                    while chunk := source.read(1024 * 1024):
                        self.wfile.write(chunk)
            except (ValueError, FileNotFoundError, PermissionError):
                self.send_error(404)
            return
        super().do_GET()


if __name__ == "__main__":
    os.chdir(WEB_ROOT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
