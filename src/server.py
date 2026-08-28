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
    "nes": ("nes", {".nes", ".zip"}),
    "snes": ("snes", {".sfc", ".smc", ".zip"}),
    "megadrive": ("segaMD", {".bin", ".gen", ".md", ".zip"}),
    "mastersystem": ("segaMS", {".sms", ".zip"}),
    "gamegear": ("segaGG", {".gg", ".zip"}),
    "gb": ("gb", {".gb", ".zip"}),
    "gbc": ("gb", {".gbc", ".zip"}),
    "gba": ("gba", {".gba", ".zip"}),
    "n64": ("n64", {".n64", ".v64", ".z64", ".zip"}),
    "atari2600": ("atari2600", {".a26", ".bin", ".zip"}),
    "atari7800": ("atari7800", {".a78", ".bin", ".zip"}),
    "lynx": ("lynx", {".lnx", ".zip"}),
    "ngp": ("ngp", {".ngp", ".ngc", ".zip"}),
    "ngpc": ("ngp", {".ngp", ".ngc", ".zip"}),
    "wswan": ("ws", {".ws", ".wsc", ".zip"}),
    "wswanc": ("ws", {".ws", ".wsc", ".zip"}),
}


def safe_join(root, relative):
    target = os.path.realpath(os.path.join(root, relative))
    resolved_root = os.path.realpath(root)
    if target != resolved_root and not target.startswith(resolved_root + os.sep):
        raise ValueError("invalid path")
    return target


def games():
    result = []
    for system, (core, extensions) in SYSTEMS.items():
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
                               "core": core, "path": relative})
    return sorted(result, key=lambda game: (game["system"], game["name"].lower()))


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
