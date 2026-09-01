#!/usr/bin/env python3
import base64
import hashlib
import html.parser
import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
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
ARTWORK_MAX_BYTES = 8 * 1024 * 1024
ARTWORK_USER_AGENT = "LAN-Batocera/1.0 (+https://github.com/HDR-Performance/lan-batocera)"
ARTWORK_REPOSITORIES = {
    "atari2600": "Atari_-_2600", "atari7800": "Atari_-_7800", "lynx": "Atari_-_Lynx",
    "nes": "Nintendo_-_Nintendo_Entertainment_System",
    "snes": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "n64": "Nintendo_-_Nintendo_64", "gb": "Nintendo_-_Game_Boy",
    "gbc": "Nintendo_-_Game_Boy_Color", "gba": "Nintendo_-_Game_Boy_Advance",
    "megadrive": "Sega_-_Mega_Drive_-_Genesis", "sega32x": "Sega_-_32X",
    "mastersystem": "Sega_-_Master_System_-_Mark_III", "gamegear": "Sega_-_Game_Gear",
    "ngp": "SNK_-_Neo_Geo_Pocket", "ngpc": "SNK_-_Neo_Geo_Pocket_Color",
    "wswan": "Bandai_-_WonderSwan", "wswanc": "Bandai_-_WonderSwan_Color",
}
ARTWORK_JOB = None
ARTWORK_LOCK = threading.Lock()

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
        metadata = gamelist_metadata(system)
        for base, _, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1].lower() not in extensions:
                    continue
                full = os.path.join(base, filename)
                relative = os.path.relpath(full, ROMS_ROOT).replace(os.sep, "/")
                details = metadata.get(os.path.realpath(full), {})
                display_name = str(details.get("name", "")).strip() or os.path.splitext(filename)[0]
                item = {"name": display_name, "system": system,
                        "systemName": system_name, "category": category,
                        "core": core, "path": relative}
                image = details.get("image")
                if image and os.path.isfile(os.path.join(folder, image)):
                    item["image"] = f"{system}/{image.replace(os.sep, '/')}"
                result.append(item)
    return sorted(result, key=lambda game: (game["category"], game["systemName"],
                                            game["name"].lower()))


def gamelist_metadata(system):
    folder = os.path.join(ROMS_ROOT, system)
    filename = os.path.join(folder, "gamelist.xml")
    if not os.path.isfile(filename):
        return {}
    try:
        root = ET.parse(filename).getroot()
    except (OSError, ET.ParseError):
        return {}
    result = {}
    for game in root.findall("game"):
        path = game.findtext("path")
        if not path:
            continue
        full = os.path.realpath(os.path.join(folder, path))
        details = {}
        name = game.findtext("name")
        if name and name.strip():
            details["name"] = name.strip()
        image = game.findtext("image")
        if image:
            media = os.path.normpath(image[2:] if image.startswith("./") else image)
            if not media.startswith(".." + os.sep) and media != "..":
                details["image"] = media
        result[full] = details
    return result


def gamelist_artwork(system):
    return {path: details["image"] for path, details in gamelist_metadata(system).items()
            if details.get("image")}


def artwork_name_candidates(name):
    base = os.path.splitext(os.path.basename(name))[0]
    candidates = [base]
    cleaned = re.sub(r"^\d{3,4}\s*-\s*", "", base)
    cleaned = re.sub(r"\s*\[[^\]]+\]", "", cleaned).strip()
    candidates.append(cleaned)
    regions = {"(U)": "(USA)", "(E)": "(Europe)", "(J)": "(Japan)",
               "(UE)": "(USA, Europe)", "(JU)": "(Japan, USA)"}
    expanded = cleaned
    for old, new in regions.items():
        expanded = expanded.replace(old, new)
    candidates.append(expanded)
    candidates.append(re.sub(r"\s*\([^)]*\)\s*$", "", expanded).strip())
    result = []
    for candidate in candidates:
        candidate = re.sub(r'[&*/:`<>?\\|\"]', "_", candidate).strip().rstrip(".")
        if candidate and candidate not in result:
            result.append(candidate)
    return result


def artwork_title_key(name):
    title = os.path.splitext(os.path.basename(name))[0]
    title = re.sub(r"\s*#\s*(N64|SNES|NES|GBA|GBC|GB|32X|MD|SMS|GG)\s*$", "", title,
                   flags=re.IGNORECASE)
    title = re.sub(r"^\d{3,4}\s*-\s*", "", title)
    title = re.sub(r"\s*[\[(].*?[\])]", "", title)
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


class _ArtworkListingParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        name = urllib.parse.unquote(href.rsplit("/", 1)[-1])
        if name.lower().endswith(".png"):
            self.names.append(os.path.splitext(name)[0])


def artwork_catalog(repository, opener=urllib.request.urlopen):
    url = "https://thumbnails.libretro.com/" + urllib.parse.quote(repository.replace("_", " ")) + "/Named_Boxarts/"
    request = urllib.request.Request(url, headers={"User-Agent": ARTWORK_USER_AGENT})
    with opener(request, timeout=30) as response:
        data = response.read(16 * 1024 * 1024)
    parser = _ArtworkListingParser()
    parser.feed(data.decode("utf-8", "replace"))
    choices = {}
    for name in parser.names:
        key = artwork_title_key(name)
        if not key:
            continue
        rank = (0 if "(USA" in name else 1 if "(World" in name else
                2 if "(Europe" in name else 3 if "(Japan" in name else 4)
        if key not in choices or rank < choices[key][0]:
            choices[key] = (rank, name)
    return {key: value[1] for key, value in choices.items()}


def _download_artwork(repository, candidates, opener=urllib.request.urlopen):
    for candidate in candidates:
        encoded = urllib.parse.quote(candidate + ".png", safe="'(),!$-._~")
        url = (f"https://raw.githubusercontent.com/libretro-thumbnails/{repository}/master/"
               f"Named_Boxarts/{encoded}")
        request = urllib.request.Request(url, headers={"User-Agent": ARTWORK_USER_AGENT})
        try:
            with opener(request, timeout=20) as response:
                length = int(response.headers.get("Content-Length", "0") or 0)
                if length > ARTWORK_MAX_BYTES:
                    continue
                data = response.read(ARTWORK_MAX_BYTES + 1)
            if len(data) <= ARTWORK_MAX_BYTES and data.startswith(b"\x89PNG\r\n\x1a\n"):
                return data, candidate, url
        except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
            continue
    return None, "", ""


def _write_gamelist(system, additions):
    folder = os.path.join(ROMS_ROOT, system)
    filename = os.path.join(folder, "gamelist.xml")
    try:
        tree = ET.parse(filename) if os.path.isfile(filename) else ET.ElementTree(ET.Element("gameList"))
        root = tree.getroot()
    except (OSError, ET.ParseError) as error:
        raise RuntimeError(f"Could not read {system}/gamelist.xml: {error}")
    existing = {}
    for node in root.findall("game"):
        path = node.findtext("path")
        if path:
            existing[os.path.realpath(os.path.join(folder, path))] = node
    for rom_path, image_relative, display_name in additions:
        node = existing.get(os.path.realpath(rom_path))
        if node is None:
            node = ET.SubElement(root, "game")
            ET.SubElement(node, "path").text = "./" + os.path.relpath(rom_path, folder).replace(os.sep, "/")
            ET.SubElement(node, "name").text = display_name
        image = node.find("image")
        if image is None:
            image = ET.SubElement(node, "image")
        image.text = "./" + image_relative.replace(os.sep, "/")
    if os.path.isfile(filename):
        backup = filename + ".lan-batocera.bak"
        if not os.path.isfile(backup):
            shutil.copy2(filename, backup)
    temporary = filename + ".lan-batocera.tmp"
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    ET.parse(temporary)
    os.replace(temporary, filename)


def _artwork_worker(job, system, limit):
    repository = ARTWORK_REPOSITORIES[system]
    folder = os.path.join(ROMS_ROOT, system)
    extensions = SYSTEMS[system][3]
    existing = gamelist_artwork(system)
    targets = []
    for base, directories, files in os.walk(folder):
        directories[:] = [item for item in directories if item not in {"images", "videos", "manuals"}]
        for filename in files:
            full = os.path.join(base, filename)
            if os.path.splitext(filename)[1].lower() in extensions and os.path.realpath(full) not in existing:
                targets.append(full)
    targets.sort(key=lambda value: value.lower())
    if limit:
        targets = targets[:limit]
    job.update({"status": "running", "system": system, "total": len(targets), "processed": 0,
                "downloaded": 0, "missing": 0, "errors": [], "current": ""})
    additions = []
    image_folder = os.path.join(folder, "images")
    os.makedirs(image_folder, exist_ok=True)
    try:
        catalog = artwork_catalog(repository)
        for rom_path in targets:
            if job.get("cancel"):
                job["status"] = "cancelled"
                break
            display_name = os.path.splitext(os.path.basename(rom_path))[0]
            job["current"] = display_name
            candidates = artwork_name_candidates(display_name)
            catalog_match = catalog.get(artwork_title_key(display_name))
            if catalog_match:
                candidates.insert(0, catalog_match)
            data, matched, _url = _download_artwork(repository, candidates)
            if data:
                image_name = "lan-" + hashlib.sha1(os.path.relpath(rom_path, folder).encode()).hexdigest() + ".png"
                image_relative = os.path.join("images", image_name)
                destination = os.path.join(folder, image_relative)
                temporary = destination + ".tmp"
                with open(temporary, "wb") as output:
                    output.write(data)
                os.replace(temporary, destination)
                additions.append((rom_path, image_relative, matched or display_name))
                job["downloaded"] += 1
            else:
                job["missing"] += 1
            job["processed"] += 1
            job["updated"] = int(time.time() * 1000)
            time.sleep(0.1)
        if additions:
            _write_gamelist(system, additions)
        if job["status"] != "cancelled":
            job["status"] = "complete"
    except Exception as error:
        job["status"] = "failed"
        job["errors"].append(str(error))
    finally:
        job["current"] = ""
        job["finished"] = int(time.time() * 1000)


def start_artwork_job(system, limit=0):
    global ARTWORK_JOB
    if system not in ARTWORK_REPOSITORIES or system not in SYSTEMS:
        raise ValueError("This console does not have a configured artwork source.")
    if not os.path.isdir(os.path.join(ROMS_ROOT, system)):
        raise ValueError("That console directory is not available.")
    if native_game_status()["nativeGameRunning"]:
        raise RuntimeError("Stop the HDMI game before fetching artwork.")
    limit = max(0, min(int(limit or 0), 10000))
    with ARTWORK_LOCK:
        if ARTWORK_JOB and ARTWORK_JOB.get("status") in {"queued", "running"}:
            raise RuntimeError("Another artwork job is already running.")
        ARTWORK_JOB = {"id": uuid.uuid4().hex, "status": "queued", "cancel": False,
                       "system": system, "total": 0, "processed": 0, "downloaded": 0,
                       "missing": 0, "errors": [], "current": ""}
        threading.Thread(target=_artwork_worker, args=(ARTWORK_JOB, system, limit), daemon=True).start()
        return dict(ARTWORK_JOB)


def artwork_status():
    with ARTWORK_LOCK:
        return dict(ARTWORK_JOB) if ARTWORK_JOB else {"status": "idle"}


def artwork_systems():
    return [{"system": system, "name": SYSTEMS[system][1]}
            for system in sorted(ARTWORK_REPOSITORIES, key=lambda item: SYSTEMS[item][1])
            if system in SYSTEMS and os.path.isdir(os.path.join(ROMS_ROOT, system))]


def cancel_artwork_job():
    with ARTWORK_LOCK:
        if not ARTWORK_JOB or ARTWORK_JOB.get("status") not in {"queued", "running"}:
            return dict(ARTWORK_JOB) if ARTWORK_JOB else {"status": "idle"}
        ARTWORK_JOB["cancel"] = True
        return dict(ARTWORK_JOB)


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


def native_game_status():
    try:
        result = subprocess.run(["/usr/bin/batocera-es-swissknife", "--emupid"],
                                capture_output=True, text=True, timeout=4, check=False)
        pids = [int(value) for value in result.stdout.split() if value.isdigit() and value != "0"]
        running = bool(pids) and result.returncode != 21
        label = "Native Batocera game"
        for pid in reversed(pids):
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as source:
                    executable = source.read(4096).split(b"\0", 1)[0].decode("utf-8", "ignore")
                if executable and "emulatorlauncher" not in executable:
                    label = os.path.basename(executable)
                    break
            except OSError:
                continue
        return {"nativeGameRunning": running, "nativeGameLabel": label if running else ""}
    except (OSError, subprocess.SubprocessError):
        running = native_game_running()
        return {"nativeGameRunning": running,
                "nativeGameLabel": "Native Batocera game" if running else ""}


def stop_native_game():
    if not native_game_status()["nativeGameRunning"]:
        return {"stopped": True, "alreadyStopped": True}
    try:
        result = subprocess.run(["/usr/bin/batocera-es-swissknife", "--emukill", "8"],
                                capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"Batocera could not stop the emulator: {error}")
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if not native_game_status()["nativeGameRunning"]:
            return {"stopped": True, "methodCode": result.returncode}
        time.sleep(0.25)
    raise RuntimeError("The native emulator did not close. Use the controller to exit it and try again.")


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
            payload = json.dumps(native_game_status()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path == "/api/artwork/status":
            self._json_response(200, artwork_status())
            return
        if parsed.path == "/api/artwork/systems":
            self._json_response(200, artwork_systems())
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
        request_path = urllib.parse.urlparse(self.path).path
        if request_path == "/api/artwork/start":
            if self.headers.get("X-LAN-Batocera-Action") != "fetch-artwork":
                self._json_response(403, {"error": "Explicit artwork confirmation is required."})
                return
            try:
                request = self._json_request()
                self._json_response(202, start_artwork_job(request.get("system", ""),
                                                           request.get("limit", 0)))
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response(400, {"error": str(error) or "Could not start artwork fetch."})
            except RuntimeError as error:
                self._json_response(409, {"error": str(error)})
            return
        if request_path == "/api/artwork/cancel":
            if self.headers.get("X-LAN-Batocera-Action") != "cancel-artwork":
                self._json_response(403, {"error": "Explicit cancellation is required."})
                return
            self._json_response(202, cancel_artwork_job())
            return
        if request_path == "/api/session-stop":
            if self.headers.get("X-LAN-Batocera-Action") != "stop-native-game":
                self._json_response(403, {"error": "Explicit stop confirmation is required."})
                return
            try:
                self._json_response(200, stop_native_game())
            except RuntimeError as error:
                self._json_response(409, {"error": str(error)})
            return
        if request_path != "/api/states":
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
