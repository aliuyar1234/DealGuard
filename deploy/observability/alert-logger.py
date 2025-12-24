from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import sys
from urllib import error, request


def load_webhook_url() -> str | None:
    url = os.getenv("ALERT_WEBHOOK_URL")
    file_path = os.getenv("ALERT_WEBHOOK_URL_FILE")
    if file_path:
        try:
            url = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Failed to read ALERT_WEBHOOK_URL_FILE at {file_path}") from exc
    return url or None


def format_alert(payload: dict) -> str:
    alerts = payload.get("alerts", [])
    if not alerts:
        return "Alertmanager webhook received (no alerts)."

    lines = []
    for alert in alerts[:5]:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        name = labels.get("alertname", "alert")
        status = alert.get("status", "unknown")
        summary = annotations.get("summary") or annotations.get("description") or ""
        line = f"{name} [{status}]"
        if summary:
            line = f"{line} {summary}"
        lines.append(line)

    if len(alerts) > 5:
        lines.append(f"...and {len(alerts) - 5} more alerts.")

    return "\n".join(lines)


def send_webhook(url: str, message: str) -> None:
    data = json.dumps({"text": message}).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"Webhook responded with status {resp.status}")


WEBHOOK_URL = load_webhook_url()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        text = body.decode("utf-8", errors="replace")
        sys.stdout.write(text + "\n")
        sys.stdout.flush()

        if not WEBHOOK_URL:
            self.send_response(200)
            self.end_headers()
            return

        try:
            payload = json.loads(text) if text else {}
            message = format_alert(payload)
            send_webhook(WEBHOOK_URL, message)
        except (json.JSONDecodeError, error.URLError, RuntimeError) as exc:
            sys.stderr.write(f"Failed to forward alert: {exc}\n")
            sys.stderr.flush()
            self.send_response(502)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()


def main() -> None:
    server = HTTPServer(("0.0.0.0", 9099), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
