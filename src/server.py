#!/usr/bin/env python3
import base64
import hashlib
import json
import mimetypes
import os
import time
import urllib.parse
import uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

WEB_ROOT = "/userdata/system/emulatorjs-lan/web"
ROMS_ROOT = "/userdata/roms"
PORT = 8080
STATE_ROOT = "/userdata/saves/lan-batocera-states"
BATOCERA_SAVES_ROOT = "/userdata/saves"
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
NATIVE_STATE_SYSTEMS = {"nes", "snes", "gb", "gbc", "gba", "megadrive", "sega32x",
                        "mastersystem", "gamegear", "atari2600", "atari7800", "lynx"}
NATIVE_EMULATOR_MARKERS = ("/retroarch", "/mupen64plus", "/ppsspp", "/pcsx2",
                           "/dolphin-emu", "/duckstation", "/rpcs3", "/xemu", "/cemu")

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


def _state_game_key(game):
    return hashlib.sha256(str(game).encode("utf-8")).hexdigest()


def _state_directory(game):
    return os.path.join(STATE_ROOT, _state_game_key(game))


def _native_state_target(game):
    try:
        _core, rom_path = str(game).split(":", 1)
        system, relative = rom_path.split("/", 1)
    except ValueError:
        return None, None
    if system not in NATIVE_STATE_SYSTEMS:
        return None, None
    rom_name = os.path.splitext(os.path.basename(relative))[0]
    if not rom_name:
        return None, None
    directory = os.path.join(BATOCERA_SAVES_ROOT, system)
    os.makedirs(directory, exist_ok=True)
    base = os.path.join(directory, rom_name + ".state")
    for slot in range(100):
        candidate = base if slot == 0 else base + str(slot)
        if not os.path.exists(candidate):
            return candidate, slot
    return None, None


def _decode_state_part(value, maximum, label):
    try:
        result = base64.b64decode(value or "", validate=True)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {label} data.")
    if not result or len(result) > maximum:
        raise ValueError(f"{label.capitalize()} data is empty or too large.")
    return result


def save_state(game, name, state_data, screenshot_data=""):
    state = _decode_state_part(state_data, MAX_STATE_BYTES, "state")
    screenshot = (_decode_state_part(screenshot_data, MAX_SCREENSHOT_BYTES, "screenshot")
                  if screenshot_data else b"")
    directory = _state_directory(game)
    os.makedirs(directory, exist_ok=True)
    state_id = uuid.uuid4().hex
    created = int(time.time() * 1000)
    with open(os.path.join(directory, state_id + ".state"), "wb") as output:
        output.write(state)
    if screenshot:
        with open(os.path.join(directory, state_id + ".png"), "wb") as output:
            output.write(screenshot)
    metadata = {"id": state_id, "name": str(name or "Saved state")[:120],
                "created": created, "size": len(state), "screenshot": bool(screenshot)}
    native_path, native_slot = _native_state_target(game)
    if native_path:
        with open(native_path, "wb") as output:
            output.write(state)
        if screenshot:
            with open(native_path + ".png", "wb") as output:
                output.write(screenshot)
        metadata["nativeSlot"] = native_slot
        metadata["nativePath"] = os.path.relpath(native_path, BATOCERA_SAVES_ROOT).replace(os.sep, "/")
    temporary = os.path.join(directory, state_id + ".json.tmp")
    with open(temporary, "w", encoding="utf-8") as output:
        json.dump(metadata, output, separators=(",", ":"))
    os.replace(temporary, os.path.join(directory, state_id + ".json"))
    return metadata


def list_states(game):
    directory = _state_directory(game)
    if not os.path.isdir(directory):
        return []
    result = []
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, filename), encoding="utf-8") as source:
                item = json.load(source)
            state_id = str(item.get("id", ""))
            if (len(state_id) == 32 and state_id.isalnum() and
                    os.path.isfile(os.path.join(directory, state_id + ".state"))):
                result.append(item)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return sorted(result, key=lambda item: item.get("created", 0), reverse=True)


def delete_states(game, state_ids):
    directory = _state_directory(game)
    deleted = 0
    for state_id in set(str(item) for item in state_ids):
        if len(state_id) != 32 or not state_id.isalnum():
            continue
        removed = False
        metadata_file = os.path.join(directory, state_id + ".json")
        try:
            with open(metadata_file, encoding="utf-8") as source:
                metadata = json.load(source)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            metadata = None
        for extension in (".state", ".png", ".json", ".json.tmp"):
            try:
                os.remove(os.path.join(directory, state_id + extension))
                removed = True
            except FileNotFoundError:
                pass
        if metadata and metadata.get("nativePath"):
            native_path = os.path.realpath(os.path.join(BATOCERA_SAVES_ROOT, metadata["nativePath"]))
            native_root = os.path.realpath(BATOCERA_SAVES_ROOT)
            if native_path.startswith(native_root + os.sep):
                for filename in (native_path, native_path + ".png"):
                    try:
                        os.remove(filename)
                        removed = True
                    except FileNotFoundError:
                        pass
        deleted += int(removed)
    return deleted


def state_file(game, state_id, extension):
    if len(state_id) != 32 or not state_id.isalnum() or extension not in (".state", ".png"):
        raise FileNotFoundError
    filename = os.path.join(_state_directory(game), state_id + extension)
    if not os.path.isfile(filename):
        raise FileNotFoundError
    return filename


def native_game_running(proc_root="/proc"):
    try:
        processes = os.listdir(proc_root)
    except OSError:
        return False
    for process in processes:
        if not process.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, process, "cmdline"), "rb") as source:
                command = source.read(8192).replace(b"\0", b" ").decode("utf-8", "ignore").lower()
        except OSError:
            continue
        if any(marker in command for marker in NATIVE_EMULATOR_MARKERS):
            return True
    return False


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
        if parsed.path == "/api/session-status":
            payload = json.dumps({"nativeGameRunning": native_game_running()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path == "/api/states":
            game = urllib.parse.parse_qs(parsed.query).get("game", [""])[0]
            payload = json.dumps(list_states(game)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path in ("/api/states/data", "/api/states/screenshot"):
            query = urllib.parse.parse_qs(parsed.query)
            game, state_id = query.get("game", [""])[0], query.get("id", [""])[0]
            extension = ".state" if parsed.path.endswith("data") else ".png"
            try:
                filename = state_file(game, state_id, extension)
                size = os.path.getsize(filename)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream" if extension == ".state" else "image/png")
                self.send_header("Content-Length", str(size))
                self.end_headers()
                with open(filename, "rb") as source:
                    while chunk := source.read(1024 * 1024):
                        self.wfile.write(chunk)
            except (FileNotFoundError, PermissionError):
                self.send_error(404)
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

    def _json_request(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length < 1 or length > (MAX_STATE_BYTES + MAX_SCREENSHOT_BYTES) * 2:
            raise ValueError("Invalid request size.")
        return json.loads(self.rfile.read(length))

    def _json_response(self, status, value):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/states":
            self.send_error(404)
            return
        try:
            request = self._json_request()
            result = save_state(request.get("game", ""), request.get("name", ""),
                                request.get("state", ""), request.get("screenshot", ""))
            self._json_response(201, result)
        except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
            self._json_response(400, {"error": str(error) or "Could not save state."})

    def do_DELETE(self):
        if urllib.parse.urlparse(self.path).path != "/api/states":
            self.send_error(404)
            return
        try:
            request = self._json_request()
            deleted = delete_states(request.get("game", ""), request.get("ids", []))
            self._json_response(200, {"deleted": deleted})
        except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
            self._json_response(400, {"error": str(error) or "Could not delete states."})


if __name__ == "__main__":
    os.chdir(WEB_ROOT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
