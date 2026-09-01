#!/usr/bin/env python3
import gzip
import http.client
import json
import os
import re
import shutil
import stat
import subprocess
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

LISTEN_PORT = 8081
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8082
MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_FOLDER_UPLOAD_FILES = 10000
MAX_EXTRACTED_BYTES = 10 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 50000
SEVEN_ZIP = "/usr/bin/7z"
EXTRACT_ROOTS = {"Games": "/userdata/roms", "BIOS": "/userdata/bios"}
SOURCE_ROOTS = {"Games": "/userdata/roms", "BIOS": "/userdata/bios",
                "Saves": "/userdata/saves", "Screenshots": "/userdata/screenshots"}
FOLDER_SIZE_CACHE_SECONDS = 60
FOLDER_SIZE_CACHE = {}
FOLDER_SIZE_CACHE_LOCK = threading.Lock()
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailers", "transfer-encoding", "upgrade", "host"}
TOOLS_PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LAN Batocera Archive Tools</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#091018;color:#eef4f7;font:16px system-ui}main{width:min(700px,92vw);margin:5vh auto}a{color:#41d6c3}.card{display:grid;gap:14px;background:#111e27;border:1px solid #29404c;border-radius:14px;padding:20px;margin:18px 0}label{display:grid;gap:6px;font-weight:650}input,select,button{min-height:48px;border:1px solid #29404c;border-radius:9px;background:#172731;color:#fff;padding:10px;font:inherit}button{border-color:#41d6c3;cursor:pointer;font-weight:700}button:disabled{opacity:.55;cursor:wait}small,.result{color:#9eb1bc}.result{white-space:pre-wrap}.ok{color:#41d6c3!important}.error{color:#ff7b72!important}.warning{color:#ffd166}progress{width:100%;height:18px}</style></head><body><main><a href="/">&larr; File Manager</a><h1>Archive tools</h1><section class="card"><h2>Auto Extract Directory</h2><p>Process every ZIP in one game directory, one at a time. Each ZIP is extracted directly into the same directory and deleted only after successful extraction.</p><label>Storage area<select id="autoSource"><option>Games</option><option>BIOS</option></select></label><label>Directory path<input id="autoDirectory" required placeholder="sega32x"><small>Path relative to the selected storage area. Subdirectories are not scanned.</small></label><label><span><input id="confirmDelete" type="checkbox"> Delete each ZIP after its extraction succeeds</span></label><p class="warning">Files are never overwritten. A ZIP that fails or conflicts is kept.</p><button id="autoSubmit">Auto Extract ZIPs</button><progress id="progress" value="0" max="1" hidden></progress><div id="autoResult" class="result"></div></section><section class="card"><h2>Extract One ZIP to a Folder</h2><label>Storage area<select id="source"><option>Games</option><option>BIOS</option></select></label><label>ZIP path<input id="archive" placeholder="snes/my-rom-pack.zip"></label><label>Destination folder (optional)<input id="destination" placeholder="snes/my-rom-pack"><small>Blank creates a folder beside the ZIP using its filename.</small></label><button id="submit">Extract ZIP</button><div id="result" class="result"></div></section></main><script>
submit.onclick=async()=>{submit.disabled=true;result.className='result';result.textContent='Extracting...';try{const r=await fetch('/lan-batocera/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:source.value,archive:archive.value,destination:destination.value})}),data=await r.json();if(!r.ok)throw Error(data.error||'Extraction failed');result.className='result ok';result.textContent=`Extracted ${data.files.toLocaleString()} files (${data.bytes.toLocaleString()} bytes) to ${data.destination}` }catch(err){result.className='result error';result.textContent=err.message}finally{submit.disabled=false}};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
autoSubmit.onclick=async()=>{if(!autoDirectory.value.trim()){autoResult.className='result error';autoResult.textContent='Enter a directory path.';return}if(!confirmDelete.checked){autoResult.className='result error';autoResult.textContent='Confirm deletion of successfully extracted ZIPs.';return}autoSubmit.disabled=true;progress.hidden=false;progress.value=0;progress.max=1;autoResult.className='result';autoResult.textContent='Starting...';try{let r=await fetch('/lan-batocera/api/auto-extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:autoSource.value,directory:autoDirectory.value,deleteArchives:true})}),data=await r.json();if(!r.ok)throw Error(data.error||'Could not start');while(true){await sleep(1000);r=await fetch(`/lan-batocera/api/auto-extract?id=${encodeURIComponent(data.id)}`);data=await r.json();if(!r.ok)throw Error(data.error||'Status unavailable');progress.max=Math.max(data.total,1);progress.value=data.processed;autoResult.textContent=`${data.status==='complete'?'Finished':'Processing'} ${data.processed}/${data.total}${data.current?'\\nCurrent: '+data.current:''}\\nSucceeded: ${data.completed}  Failed: ${data.failed}`;if(data.status==='complete'){autoResult.className=data.failed?'result error':'result ok';if(data.errors.length)autoResult.textContent+='\\n\\nKept because of errors:\\n'+data.errors.map(item=>`${item.archive}: ${item.error}`).join('\\n');break}}}catch(err){autoResult.className='result error';autoResult.textContent=err.message}finally{autoSubmit.disabled=false}};
</script></body></html>'''.encode()
TOOLS_PAGE = (TOOLS_PAGE.replace(b"every ZIP", b"every ZIP or RAR")
              .replace(b"Each ZIP", b"Each archive")
              .replace(b"Delete each ZIP", b"Delete each archive")
              .replace(b"A ZIP that", b"An archive that")
              .replace(b"Auto Extract ZIPs", b"Auto Extract ZIPs and RARs")
              .replace(b"Extract One ZIP to a Folder", b"Extract One ZIP or RAR to a Folder")
              .replace(b"ZIP path", b"Archive path")
              .replace(b"snes/my-rom-pack.zip", b"sega32x/my-game.rar")
              .replace(b"Extract ZIP</button>", b"Extract Archive</button>"))
EXTRACT_JOBS = {}
EXTRACT_JOBS_LOCK = threading.Lock()
ACTIVE_EXTRACT_JOB = None

FILEBROWSER_JS_PATCHES = (
    (b'async add(e,n,i=!1){if(e||(e="/"),',
     b'async add(e,n,i=!1){if(n.length>' + str(MAX_FOLDER_UPLOAD_FILES).encode() +
     b'){yt.showError("A folder upload can contain up to 10,000 files. Split larger folders into separate uploads.");return[]}if(e||(e="/"),'),
    (b'uploadSettingsDescription(){const t=L.user.fileLoading?.maxConcurrentUpload,e=L.user.fileLoading?.uploadChunkSizeMb;',
     b'uploadSettingsDescription(){const t=Math.min(4,L.user.fileLoading?.maxConcurrentUpload||4),e=L.user.fileLoading?.uploadChunkSizeMb;'),
    (b'const u=Gr(L.user.fileLoading?.maxConcurrentUpload),d=Gr(L.user.fileLoading?.uploadChunkSizeMb)',
     b'const u=Gr(Math.min(4,L.user.fileLoading?.maxConcurrentUpload||4)),d=Gr(L.user.fileLoading?.uploadChunkSizeMb)'),
    (b'modifiedSorted(){return be.sorting().by==="modified"},durationSorted()',
     b'modifiedSorted(){return be.sorting().by==="modified"},typeSorted(){return be.sorting().by==="type"},durationSorted()'),
    (b'modifiedIcon(){return this.modifiedSorted&&this.ascOrdered?"arrow_downward":"arrow_upward"},durationIcon()',
     b'modifiedIcon(){return this.modifiedSorted&&this.ascOrdered?"arrow_downward":"arrow_upward"},typeIcon(){return this.typeSorted&&this.ascOrdered?"arrow_downward":"arrow_upward"},durationIcon()'),
    (b'||t==="modified"&&this.modifiedIcon==="arrow_upward"||t==="duration"',
     b'||t==="modified"&&this.modifiedIcon==="arrow_upward"||t==="type"&&this.typeIcon==="arrow_upward"||t==="duration"'),
    (b'],10,V2e),M("p",{class:mt([{active:r.sizeSorted},"size"])',
     b'],10,V2e),M("p",{class:mt([{active:r.typeSorted},"size"]),role:"button",tabindex:"0",onClick:a=>r.sort("type"),title:"Sort by file type","aria-label":"Sort by file type"},[r.typeSorted?(H(),J("i",G2e,j(r.typeIcon),1)):Me("",!0),M("span",null,"Type")],10,V2e),M("p",{class:mt([{active:r.sizeSorted},"size"])'),
    (b'this.PROGRESS_TIMEOUT_MS=1e4', b'this.PROGRESS_TIMEOUT_MS=12e4'),
    (b'const e=L.user.fileLoading?.maxConcurrentUpload||3;',
     b'const e=Math.min(4,L.user.fileLoading?.maxConcurrentUpload||4);'),
    (b'r=ui(()=>zs.queue),a=Gr(!1)', b'r=ui(()=>[...zs.queue].reverse()),a=Gr(!1)'),
    (b'const T=ui(()=>r.value.some(oe=>oe.status==="completed"))',
     b'const P=ui(()=>{const oe=r.value.filter(F=>F.type!=="directory"),F=oe.length,he=oe.filter(U=>U.status==="completed").length,ge=oe.reduce((U,Z)=>U+(Z.size||0),0),U=oe.reduce((Z,Ve)=>Z+(Ve.status==="completed"?(Ve.size||0):Math.min(Ve.size||0,(Ve.progress||0)/100*(Ve.size||0))),0);return{percent:ge?Math.min(100,Math.round(U/ge*100)):0,completed:he,total:F}}),T=ui(()=>r.value.some(oe=>oe.status==="completed"))'),
    (b'clearCompleted:A,hasCompleted:T,hasClearable:C,showConflictPrompt:o,',
     b'clearCompleted:A,overallProgress:P,hasCompleted:T,hasClearable:C,showConflictPrompt:o,'),
    (b'],34)]),i.files.length>0?(H(),J("div",Nhe,',
     b'],34)]),i.files.length>0?(H(),J("div",{key:"lan-overall-progress",style:{padding:"10px 12px 4px"}},[M("p",{style:{margin:"0 0 6px","font-size":".9rem","font-weight":"600"}},"Overall upload: "+j(i.overallProgress.percent)+"% - "+j(i.overallProgress.completed)+" of "+j(i.overallProgress.total)+" files complete",1),ft(l,{val:i.overallProgress.percent,unit:"%",max:100,status:i.overallProgress.percent>=100?"completed":"uploading","text-position":"inside",size:"14"},null,8,["val","status"])])):Me("",!0),i.files.length>0?(H(),J("div",Nhe,'),
    (b'e.connectionIssue=!0,this.pause(e.id),e.errorDetails="Connection stalled - upload paused. Click resume to retry."',
     b'e.connectionIssue=!0,this.isOverallPaused=!0,this.pause(e.id),e.errorDetails="Connection stalled - queue paused. Resume to retry this file before continuing."'),
    (b'this.queue.some(r=>r.status==="error"||r.status==="conflict")||ae.setReload(!0),this.hadActiveUploads=!1',
     b'ae.setReload(!0),QH().then(r=>ae.updateSourceInfo(r)).catch(()=>{}),this.hadActiveUploads=!1'),
    (b'type:"range",min:"1",max:"10",onChange:',
     b'type:"range",min:"1",max:"4",onChange:'),
    (b'type:"range",min:"1",max:"10",placeholder:',
     b'type:"range",min:"1",max:"4",placeholder:'),
)

FILEBROWSER_BRANDING_PATCHES = (
    # LAN Batocera pins and tests its FileBrowser integration. Do not advertise
    # an untested upstream binary from inside this customized frontend.
    (b'shouldShow(){return It.updateAvailable!==""&&L.user.permissions.admin&&L.seenUpdate!==It.updateAvailable&&!L.user.disableUpdateNotifications}',
     b'shouldShow(){return false}'),
)


def _patch_file_type_sort(path, body):
    if not (path.startswith("/public/static/assets/index-") and path.endswith(".js")):
        return body, False
    changed = False
    if all(old in body for old, _new in FILEBROWSER_JS_PATCHES):
        for old, new in FILEBROWSER_JS_PATCHES:
            body = body.replace(old, new, 1)
        changed = True
    for old, new in FILEBROWSER_BRANDING_PATCHES:
        if old in body:
            body = body.replace(old, new, 1)
            changed = True
    return body, changed


def _version_filebrowser_html(body):
    pattern = rb'(/public/static/assets/index-[^"\' ?]+\.js)(["\'])'
    updated, count = re.subn(pattern, rb'\1?lan-batocera-ui=5\2', body, count=1)
    return updated, count == 1


def _clear_folder_size_cache():
    with FOLDER_SIZE_CACHE_LOCK:
        FOLDER_SIZE_CACHE.clear()


def _recursive_file_size(directory):
    total = 0
    for base, directories, files in os.walk(directory, followlinks=False):
        directories[:] = [name for name in directories
                          if not os.path.islink(os.path.join(base, name))]
        for name in files:
            filename = os.path.join(base, name)
            try:
                if not os.path.islink(filename):
                    total += os.path.getsize(filename)
            except OSError:
                continue
    return total


def _directory_sizes(source, relative, folder_names):
    root = SOURCE_ROOTS.get(source)
    if root is None:
        return None
    try:
        directory, normalized = _safe_root_path(root, relative, True)
    except (ValueError, OSError):
        return None
    names = tuple(sorted(str(name) for name in folder_names))
    cache_key = (source, normalized, names)
    now = time.monotonic()
    with FOLDER_SIZE_CACHE_LOCK:
        cached = FOLDER_SIZE_CACHE.get(cache_key)
        if cached and now - cached[0] < FOLDER_SIZE_CACHE_SECONDS:
            return cached[1]
    sizes = {}
    for name in names:
        try:
            child, _unused = _safe_root_path(directory, name, True)
            sizes[name] = _recursive_file_size(child)
        except (ValueError, OSError):
            continue
    with FOLDER_SIZE_CACHE_LOCK:
        FOLDER_SIZE_CACHE[cache_key] = (now, sizes)
    return sizes


def _patch_resource_folder_sizes(path, body):
    parsed = urlsplit(path)
    if parsed.path != "/api/resources":
        return body, False
    from urllib.parse import parse_qs
    query = parse_qs(parsed.query)
    source = query.get("source", [""])[0]
    relative = query.get("path", ["/"])[0]
    try:
        payload = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return body, False
    folders = payload.get("folders")
    if not isinstance(folders, list):
        return body, False
    sizes = _directory_sizes(source, relative, [item.get("name", "") for item in folders])
    if sizes is None:
        return body, False
    for item in folders:
        if item.get("name") in sizes:
            item["size"] = sizes[item["name"]]
    direct_files = payload.get("files", [])
    direct_size = sum(item.get("size", 0) for item in direct_files
                      if isinstance(item, dict) and isinstance(item.get("size", 0), (int, float)))
    payload["size"] = int(direct_size + sum(sizes.values()))
    return json.dumps(payload, separators=(",", ":")).encode(), True


def _directory_from_referer(referer):
    try:
        path = unquote(urlsplit(referer or "").path)
    except ValueError:
        return None
    prefix = "/files/"
    if not path.startswith(prefix):
        return None
    parts = path[len(prefix):].strip("/").split("/", 1)
    if not parts or parts[0] not in EXTRACT_ROOTS:
        return None
    directory = parts[1].strip("/") if len(parts) > 1 else ""
    return {"source": parts[0], "directory": directory}


def _tools_page_for_context(referer):
    context = _directory_from_referer(referer)
    if context is None:
        return TOOLS_PAGE
    source = json.dumps(context["source"]).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    directory = json.dumps(context["directory"]).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    auto_start = ("<script>autoSource.value=" + source + ";autoDirectory.value=" + directory +
                  ";confirmDelete.checked=true;autoSubmit.click();</script>").encode()
    return TOOLS_PAGE.replace(b"</body>", auto_start + b"</body>")


def _safe_root_path(root, relative, require_directory=False):
    relative = str(relative or "").strip().strip("/")
    path = os.path.realpath(os.path.join(root, relative))
    root_path = os.path.realpath(root)
    if path != root_path and not path.startswith(root_path + os.sep):
        raise ValueError("Invalid path.")
    if require_directory and not os.path.isdir(path):
        raise ValueError("Directory was not found in the selected storage area.")
    return path, relative


def _validated_zip_entries(package):
    entries = package.infolist()
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise ValueError("Archive contains too many entries.")
    total = sum(entry.file_size for entry in entries)
    if total > MAX_EXTRACTED_BYTES:
        raise ValueError("Archive expands beyond the 10 GiB safety limit.")
    for entry in entries:
        parts = PurePosixPath(entry.filename.replace("\\", "/")).parts
        if not parts or entry.filename.startswith(("/", "\\")) or ".." in parts:
            raise ValueError("Archive contains an unsafe path.")
        if stat.S_ISLNK(entry.external_attr >> 16):
            raise ValueError("Archive contains a symbolic link.")
    return entries, total


def _validate_archive_path(name):
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if (not parts or normalized.startswith("/") or ".." in parts or
            (len(normalized) > 2 and normalized[1] == ":" and normalized[2] == "/")):
        raise ValueError("Archive contains an unsafe path.")
    return parts


def _parse_7z_listing(output):
    if "----------" not in output:
        raise ValueError("RAR metadata could not be read.")
    records = []
    for block in output.split("----------", 1)[1].strip().split("\n\n"):
        record = {}
        for line in block.splitlines():
            if " = " in line:
                key, value = line.split(" = ", 1)
                record[key] = value
        if record.get("Path"):
            records.append(record)
    if len(records) > MAX_ARCHIVE_ENTRIES:
        raise ValueError("Archive contains too many entries.")
    total = 0
    for record in records:
        _validate_archive_path(record["Path"])
        if record.get("Symbolic Link") or record.get("Hard Link"):
            raise ValueError("Archive contains a link.")
        if record.get("Encrypted") == "+":
            raise ValueError("Password-protected archives are not supported.")
        if record.get("Split Before") == "+" or record.get("Split After") == "+":
            raise ValueError("Multi-volume RAR archives are not supported.")
        try:
            total += int(record.get("Size", "0"))
        except ValueError as error:
            raise ValueError("RAR contains invalid size metadata.") from error
    if total > MAX_EXTRACTED_BYTES:
        raise ValueError("Archive expands beyond the 10 GiB safety limit.")
    return records, total


def _extract_to_new_directory(archive, destination):
    with zipfile.ZipFile(archive) as package:
        entries, total = _validated_zip_entries(package)
        os.makedirs(destination)
        files = 0
        try:
            for entry in entries:
                parts = PurePosixPath(entry.filename.replace("\\", "/")).parts
                target = os.path.realpath(os.path.join(destination, *parts))
                if not target.startswith(destination + os.sep):
                    raise ValueError("Archive contains an unsafe path.")
                if entry.is_dir():
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with package.open(entry) as source, open(target, "xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                files += 1
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
    return files, total


def _extract_rar_to_new_directory(archive, destination):
    if not os.path.isfile(SEVEN_ZIP):
        raise ValueError("RAR extraction is unavailable on this device.")
    listing = subprocess.run(
        [SEVEN_ZIP, "l", "-slt", "-sccUTF-8", "--", archive],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=300, check=False)
    if listing.returncode != 0:
        raise ValueError("RAR metadata check failed: " + listing.stdout.strip()[-300:])
    records, listed_total = _parse_7z_listing(listing.stdout)
    os.makedirs(destination)
    try:
        extracted = subprocess.run(
            [SEVEN_ZIP, "x", "-y", "-sccUTF-8", "-o" + destination, "--", archive],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=21600, check=False)
        if extracted.returncode != 0:
            raise ValueError("RAR extraction failed: " + extracted.stdout.strip()[-300:])
        files = 0
        actual_total = 0
        for current, directories, filenames in os.walk(destination, followlinks=False):
            for name in directories + filenames:
                path = os.path.join(current, name)
                if stat.S_ISLNK(os.lstat(path).st_mode):
                    raise ValueError("Archive extracted a symbolic link.")
                real = os.path.realpath(path)
                if not real.startswith(destination + os.sep):
                    raise ValueError("Archive contains an unsafe path.")
            for name in filenames:
                files += 1
                actual_total += os.path.getsize(os.path.join(current, name))
                if actual_total > MAX_EXTRACTED_BYTES:
                    raise ValueError("Archive expands beyond the 10 GiB safety limit.")
        expected_files = sum(record.get("Folder") != "+" for record in records)
        if files != expected_files or actual_total != listed_total:
            raise ValueError("RAR extraction did not match its validated contents.")
        return files, actual_total
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _extract_beside_archive(archive, extractor):
    parent = os.path.dirname(archive)
    staging = os.path.join(parent, ".lan-batocera-extract-" + uuid.uuid4().hex)
    moved = []
    try:
        files, total = extractor(archive, staging)
        names = os.listdir(staging)
        collisions = [name for name in names if os.path.exists(os.path.join(parent, name))]
        if collisions:
            preview = ", ".join(collisions[:3])
            raise ValueError("Output already exists: " + preview)
        try:
            for name in names:
                source = os.path.join(staging, name)
                destination = os.path.join(parent, name)
                os.rename(source, destination)
                moved.append((source, destination))
        except Exception:
            for source, destination in reversed(moved):
                if os.path.exists(destination):
                    os.rename(destination, source)
            raise
        os.rmdir(staging)
        os.remove(archive)
        return files, total
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _extract_zip_beside_archive(archive):
    return _extract_beside_archive(archive, _extract_to_new_directory)


def _extract_archive_beside_archive(archive):
    extension = os.path.splitext(archive)[1].lower()
    if extension == ".zip":
        return _extract_beside_archive(archive, _extract_to_new_directory)
    if extension == ".rar":
        return _extract_beside_archive(archive, _extract_rar_to_new_directory)
    raise ValueError("Unsupported archive type.")


def _run_auto_extract(job_id, directory):
    global ACTIVE_EXTRACT_JOB
    with EXTRACT_JOBS_LOCK:
        job = EXTRACT_JOBS[job_id]
        job["status"] = "running"
    try:
        archives = sorted((entry.path for entry in os.scandir(directory)
                           if entry.is_file(follow_symlinks=False) and
                           os.path.splitext(entry.name)[1].lower() in (".zip", ".rar")),
                          key=lambda value: value.lower())
        with EXTRACT_JOBS_LOCK:
            job["total"] = len(archives)
        for archive in archives:
            with EXTRACT_JOBS_LOCK:
                job["current"] = os.path.basename(archive)
            try:
                files, total = _extract_archive_beside_archive(archive)
                with EXTRACT_JOBS_LOCK:
                    job["completed"] += 1
                    job["files"] += files
                    job["bytes"] += total
            except (ValueError, zipfile.BadZipFile, OSError, subprocess.SubprocessError) as error:
                with EXTRACT_JOBS_LOCK:
                    job["failed"] += 1
                    job["errors"].append({"archive": os.path.basename(archive),
                                          "error": str(error) or "Extraction failed."})
            with EXTRACT_JOBS_LOCK:
                job["processed"] += 1
    except OSError as error:
        with EXTRACT_JOBS_LOCK:
            job["errors"].append({"archive": "", "error": str(error) or "Directory scan failed."})
            job["failed"] += 1
    finally:
        with EXTRACT_JOBS_LOCK:
            job["current"] = ""
            job["status"] = "complete"
            ACTIVE_EXTRACT_JOB = None


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _request_size(self):
        candidates = [self.headers.get("X-File-Total-Size"), self.headers.get("Upload-Length")]
        if "/api/resources" in self.path or "/api/tus" in self.path:
            candidates.append(self.headers.get("Content-Length"))
        sizes = []
        for value in candidates:
            if value:
                try:
                    sizes.append(int(value))
                except ValueError:
                    pass
        return max(sizes, default=0)

    def _reject_large_file(self):
        body = b'{"error":"Files larger than 1 GiB are not allowed."}'
        self.send_response(413, "File exceeds 1 GiB limit")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True

    def _authenticated(self):
        connection = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=10)
        headers = {"Host": self.headers.get("Host", f"{BACKEND_HOST}:{BACKEND_PORT}")}
        for name in ("Cookie", "Authorization"):
            if self.headers.get(name):
                headers[name] = self.headers[name]
        try:
            connection.request("GET", "/api/users?id=self", headers=headers)
            response = connection.getresponse()
            response.read()
            return response.status == 200
        except (ConnectionError, TimeoutError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    def _tools_page(self):
        if not self._authenticated():
            self.send_response(302)
            self.send_header("Location", "/login?redirect=/lan-batocera-tools")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = b'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LAN Batocera ZIP Extractor</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#091018;color:#eef4f7;font:16px system-ui}main{width:min(620px,92vw);margin:7vh auto}a{color:#41d6c3}form{display:grid;gap:14px;background:#111e27;border:1px solid #29404c;border-radius:14px;padding:20px}label{display:grid;gap:6px;font-weight:650}input,select,button{min-height:48px;border:1px solid #29404c;border-radius:9px;background:#172731;color:#fff;padding:10px;font:inherit}button{border-color:#41d6c3;cursor:pointer}small,#result{color:#9eb1bc}#result{margin-top:16px;white-space:pre-wrap}.ok{color:#41d6c3!important}.error{color:#ff7b72!important}</style></head><body><main><a href="/">\xe2\x86\x90 File Manager</a><h1>Extract a ZIP archive</h1><p>Extract an uploaded ZIP into Games or BIOS. Existing destination folders are protected from overwrite.</p><form id="form"><label>Storage area<select id="source"><option>Games</option><option>BIOS</option></select></label><label>ZIP path<input id="archive" required placeholder="snes/my-rom-pack.zip"><small>Path relative to the selected storage area.</small></label><label>Destination folder (optional)<input id="destination" placeholder="snes/my-rom-pack"><small>Blank creates a folder beside the ZIP using its filename.</small></label><button id="submit">Extract ZIP</button></form><div id="result"></div></main><script>form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;result.className='';result.textContent='Extracting...';try{const r=await fetch('/lan-batocera/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:source.value,archive:archive.value,destination:destination.value})}),data=await r.json();if(!r.ok)throw Error(data.error||'Extraction failed');result.className='ok';result.textContent=`Extracted ${data.files.toLocaleString()} files (${data.bytes.toLocaleString()} bytes) to ${data.destination}` }catch(err){result.className='error';result.textContent=err.message}finally{submit.disabled=false}};</script></body></html>'''
        body = _tools_page_for_context(self.headers.get("Referer"))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _extract_zip(self):
        if not self._authenticated():
            self._send_json(401, {"error": "Login required."})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length < 1 or length > 65536:
            self._send_json(400, {"error": "Invalid request."})
            return
        try:
            request = json.loads(self.rfile.read(length))
            source_name = request.get("source", "")
            root = EXTRACT_ROOTS[source_name]
            archive_relative = str(request.get("archive", "")).strip().strip("/")
            extension = os.path.splitext(archive_relative)[1].lower()
            if extension not in (".zip", ".rar"):
                raise ValueError("Select a .zip or .rar archive.")
            archive = os.path.realpath(os.path.join(root, archive_relative))
            if not archive.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(archive):
                raise ValueError("Archive was not found in the selected storage area.")
            destination_relative = str(request.get("destination", "")).strip().strip("/")
            if not destination_relative:
                destination_relative = os.path.join(os.path.dirname(archive_relative),
                                                    os.path.splitext(os.path.basename(archive_relative))[0])
            destination = os.path.realpath(os.path.join(root, destination_relative))
            if not destination.startswith(os.path.realpath(root) + os.sep):
                raise ValueError("Invalid destination path.")
            if os.path.exists(destination):
                self._send_json(409, {"error": "Destination already exists; choose a new folder."})
                return
            extractor = _extract_to_new_directory if extension == ".zip" else _extract_rar_to_new_directory
            files, total = extractor(archive, destination)
            self._send_json(200, {"files": files, "bytes": total,
                                  "destination": destination_relative.replace(os.sep, "/")})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile,
                OSError, subprocess.SubprocessError) as error:
            self._send_json(400, {"error": str(error) or "Extraction failed."})

    def _start_auto_extract(self):
        global ACTIVE_EXTRACT_JOB
        if not self._authenticated():
            self._send_json(401, {"error": "Login required."})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length < 1 or length > 65536:
            self._send_json(400, {"error": "Invalid request."})
            return
        try:
            request = json.loads(self.rfile.read(length))
            root = EXTRACT_ROOTS[request.get("source", "")]
            if request.get("deleteArchives") is not True:
                raise ValueError("Archive deletion must be confirmed.")
            directory, relative = _safe_root_path(root, request.get("directory"), True)
            job_id = uuid.uuid4().hex
            job = {"id": job_id, "directory": relative.replace(os.sep, "/"),
                   "status": "queued", "total": 0, "processed": 0,
                   "completed": 0, "failed": 0, "files": 0, "bytes": 0,
                   "current": "", "errors": []}
            with EXTRACT_JOBS_LOCK:
                if ACTIVE_EXTRACT_JOB is not None:
                    self._send_json(409, {"error": "Another Auto Extract job is already running."})
                    return
                ACTIVE_EXTRACT_JOB = job_id
                EXTRACT_JOBS[job_id] = job
            threading.Thread(target=_run_auto_extract, args=(job_id, directory), daemon=True).start()
            self._send_json(202, {"id": job_id})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as error:
            self._send_json(400, {"error": str(error) or "Could not start Auto Extract."})

    def _auto_extract_status(self):
        if not self._authenticated():
            self._send_json(401, {"error": "Login required."})
            return
        from urllib.parse import parse_qs, urlsplit
        job_id = parse_qs(urlsplit(self.path).query).get("id", [""])[0]
        with EXTRACT_JOBS_LOCK:
            job = EXTRACT_JOBS.get(job_id)
            snapshot = dict(job) if job else None
            if snapshot:
                snapshot["errors"] = list(job["errors"])
        if not snapshot:
            self._send_json(404, {"error": "Auto Extract job was not found."})
            return
        self._send_json(200, snapshot)

    def _forward(self):
        if self._request_size() > MAX_FILE_BYTES:
            self._reject_large_file()
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        headers = {key: value for key, value in self.headers.items()
                   if key.lower() not in HOP_HEADERS}
        is_frontend_script = (self.path.startswith("/public/static/assets/index-") and
                              self.path.split("?", 1)[0].endswith(".js"))
        is_resource_listing = (self.command == "GET" and
                               self.path.split("?", 1)[0] == "/api/resources")
        if is_frontend_script or is_resource_listing:
            headers["Accept-Encoding"] = "identity"
        headers["Host"] = self.headers.get("Host", f"{BACKEND_HOST}:{BACKEND_PORT}")
        connection = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=300)
        try:
            connection.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            for key, value in headers.items():
                connection.putheader(key, value)
            connection.endheaders()
            remaining = length
            while remaining:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                connection.send(chunk)
                remaining -= len(chunk)
            response = connection.getresponse()
            is_frontend_html = "text/html" in response.getheader("Content-Type", "").lower()
            response_body = response.read() if (is_frontend_script or is_frontend_html or
                                                is_resource_listing) else None
            patched = False
            if response_body is not None:
                candidate = response_body
                if response.getheader("Content-Encoding", "").lower() == "gzip":
                    try:
                        candidate = gzip.decompress(response_body)
                    except (OSError, EOFError):
                        candidate = response_body
                if is_frontend_script:
                    candidate, patched = _patch_file_type_sort(self.path.split("?", 1)[0], candidate)
                elif is_frontend_html:
                    candidate, patched = _version_filebrowser_html(candidate)
                elif is_resource_listing and response.status == 200:
                    candidate, patched = _patch_resource_folder_sizes(self.path, candidate)
                if patched:
                    response_body = candidate
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS and not (patched and key.lower() in
                                                            {"content-length", "content-encoding", "etag"}):
                    self.send_header(key, value)
            if patched:
                self.send_header("Content-Length", str(len(response_body)))
                self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            if response_body is not None:
                self.wfile.write(response_body)
            else:
                while chunk := response.read(1024 * 1024):
                    self.wfile.write(chunk)
        except (ConnectionError, TimeoutError, http.client.HTTPException):
            self.send_error(502, "File manager backend unavailable")
        finally:
            connection.close()
            self.close_connection = True
            if self.command in {"POST", "PUT", "PATCH", "DELETE"} and (
                    "/api/resources" in self.path or "/api/tus" in self.path):
                _clear_folder_size_cache()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/lan-batocera-tools":
            self._tools_page()
        elif path == "/lan-batocera/api/auto-extract":
            self._auto_extract_status()
        else:
            self._forward()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/lan-batocera/api/extract":
            self._extract_zip()
        elif path == "/lan-batocera/api/auto-extract":
            self._start_auto_extract()
        else:
            self._forward()

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Proxy).serve_forever()
