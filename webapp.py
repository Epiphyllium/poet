"""Zero-framework local web UI and JSON API for the poem generator."""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from poet import generate_poem
from poet.trace import get_trace, last_trace_id, list_traces

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"


class PoetHandler(BaseHTTPRequestHandler):
    server_version = "PoetStudio/0.1"

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            resolved.relative_to(WEB_ROOT.resolve())
        except (ValueError, OSError):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = resolved.read_bytes()
        content_type, _ = mimetypes.guess_type(resolved.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = unquote(urlparse(self.path).path)
        if path == "/api/traces":
            self._json({"traces": list_traces()})
            return
        if path.startswith("/api/traces/"):
            trace_id = path.rsplit("/", 1)[-1]
            trace = get_trace(trace_id)
            if trace is None:
                self._json({"error": "Trace 不存在或已过期"}, HTTPStatus.NOT_FOUND)
            else:
                self._json(trace)
            return

        pages = {
            "/": WEB_ROOT / "index.html",
            "/traces": WEB_ROOT / "traces.html",
            "/traces/": WEB_ROOT / "traces.html",
        }
        if path in pages:
            self._serve_file(pages[path])
            return
        if path.startswith("/assets/"):
            self._serve_file(WEB_ROOT / path.removeprefix("/assets/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/api/generate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 64_000:
                raise ValueError("请求体大小不合法")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            topic = value.get("topic")
            if not isinstance(topic, str):
                raise ValueError("topic 必须是字符串")
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        poem = generate_poem(topic)
        self._json({"poem": poem, "trace_id": last_trace_id()})

    def log_message(self, fmt: str, *args: object) -> None:
        logging.getLogger("poet.web").info("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="五言诗生成系统 Web 界面")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    server = ThreadingHTTPServer((args.host, args.port), PoetHandler)
    print(f"五言诗试验台：http://{args.host}:{args.port}")
    print(f"运行行迹：http://{args.host}:{args.port}/traces")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
