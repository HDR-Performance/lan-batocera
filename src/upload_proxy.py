#!/usr/bin/env python3
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_PORT = 8081
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8082
MAX_FILE_BYTES = 1024 * 1024 * 1024
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

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Proxy).serve_forever()
