#!/usr/bin/env python3
import http.client
import json
import os
import shutil
import stat
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath

LISTEN_PORT = 8081
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8082
MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_EXTRACTED_BYTES = 10 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 50000
EXTRACT_ROOTS = {"Games": "/userdata/roms", "BIOS": "/userdata/bios"}
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailers", "transfer-encoding", "upgrade", "host"}


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
            if not archive_relative.lower().endswith(".zip"):
                raise ValueError("Select a .zip archive.")
            archive = os.path.realpath(os.path.join(root, archive_relative))
            if not archive.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(archive):
                raise ValueError("ZIP archive was not found in the selected storage area.")
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
            with zipfile.ZipFile(archive) as package:
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
                os.makedirs(destination)
                files = 0
                try:
                    for entry in entries:
                        target = os.path.realpath(os.path.join(destination, *PurePosixPath(entry.filename.replace("\\", "/")).parts))
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
            self._send_json(200, {"files": files, "bytes": total,
                                  "destination": destination_relative.replace(os.sep, "/")})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, OSError) as error:
            self._send_json(400, {"error": str(error) or "Extraction failed."})

    def _forward(self):
        if self._request_size() > MAX_FILE_BYTES:
            self._reject_large_file()
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        headers = {key: value for key, value in self.headers.items()
                   if key.lower() not in HOP_HEADERS}
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
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            while chunk := response.read(1024 * 1024):
                self.wfile.write(chunk)
        except (ConnectionError, TimeoutError, http.client.HTTPException):
            self.send_error(502, "File manager backend unavailable")
        finally:
            connection.close()
            self.close_connection = True

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/lan-batocera-tools":
            self._tools_page()
        else:
            self._forward()

    def do_POST(self):
        if self.path.split("?", 1)[0] == "/lan-batocera/api/extract":
            self._extract_zip()
        else:
            self._forward()

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Proxy).serve_forever()
