#!/usr/bin/env python3
"""
Nanobot Status Dashboard with Tailscale Authentication
High-quality, production-ready version
"""

from __future__ import annotations

import os
import json
import psutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from flask import Flask, render_template, jsonify, request, send_from_directory
import subprocess
import urllib.request

# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ----------------------------------------------------------------------
# Paths / Config
# ----------------------------------------------------------------------

NANOBOT_DIR = Path.home() / ".nanobot"
CONFIG_FILE = NANOBOT_DIR / "config.json"
CRON_JOBS_FILE = NANOBOT_DIR / "cron" / "jobs.json"
SESSIONS_DIR = NANOBOT_DIR / "sessions"
PROJECT_DIR = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_DIR / "static"

REQUIRE_TAILSCALE_AUTH = os.getenv("REQUIRE_TAILSCALE_AUTH", "true").lower() == "true"

# ----------------------------------------------------------------------
# Simple TTL Cache (thread-safe)
# ----------------------------------------------------------------------

class TTLCache:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str, ttl: int, loader: Callable[[], Any]) -> Any:
        now = datetime.now().timestamp()
        with self._lock:
            if key in self._data and now < self._expires.get(key, 0):
                return self._data[key]

        value = loader()

        with self._lock:
            self._data[key] = value
            self._expires[key] = now + ttl

        return value


cache = TTLCache()

# ----------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------

def check_tailscale_auth() -> bool:
    if not REQUIRE_TAILSCALE_AUTH:
        return True

    if request.headers.get("X-Tailscale-User"):
        return True

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if not client_ip:
        return False

    ip = client_ip.split(",")[0].strip()
    return (
        ip.startswith("100.")
        or ip in {"127.0.0.1", "::1", "localhost"}
    )

# ----------------------------------------------------------------------
# Nanobot Info
# ----------------------------------------------------------------------

def get_nanobot_process_info() -> Dict[str, Any]:
    for proc in psutil.process_iter(
        ["pid", "cmdline", "create_time", "memory_info"]
    ):
        try:
            cmdline = proc.info.get("cmdline") or []
            if "nanobot" not in " ".join(cmdline).lower():
                continue

            p = psutil.Process(proc.info["pid"])
            cpu = p.cpu_percent(interval=0.2)
            mem_mb = round(proc.info["memory_info"].rss / 1024 / 1024, 2)
            mem_pct = round(p.memory_percent(), 1)

            return {
                "running": True,
                "pid": proc.info["pid"],
                "uptime_seconds": int(
                    datetime.now().timestamp() - proc.info["create_time"]
                ),
                "memory_mb": mem_mb,
                "memory_percent": mem_pct,
                "cpu_percent": round(cpu, 1),
            }

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {"running": False}


def get_nanobot_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open(encoding="utf-8") as f:
            config = json.load(f)

        return {
            "gateway": config.get("gateway", {}),
            "channels": {
                name: {"enabled": ch.get("enabled", False)}
                for name, ch in config.get("channels", {}).items()
            },
            "model": config.get("agents", {})
                          .get("defaults", {})
                          .get("model", "Unknown"),
        }
    except json.JSONDecodeError:
        return {}


def get_cron_jobs() -> Dict[str, Any]:
    if not CRON_JOBS_FILE.exists():
        return {"count": 0, "jobs": []}

    try:
        with CRON_JOBS_FILE.open(encoding="utf-8") as f:
            data = json.load(f)

        jobs = data.get("jobs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not isinstance(jobs, list):
            jobs = []

        out = []
        for j in jobs:
            state = j.get("state") or {}
            next_ms = state.get("nextRunAtMs")
            last_ms = state.get("lastRunAtMs")
            out.append({
                "id": j.get("id"),
                "name": j.get("name"),
                "enabled": j.get("enabled", True),
                "expr": (j.get("schedule") or {}).get("expr"),
                "nextRunAtMs": next_ms,
                "lastRunAtMs": last_ms,
                "lastStatus": state.get("lastStatus"),
                "lastError": state.get("lastError"),
            })
        return {"count": len(jobs), "jobs": out}
    except json.JSONDecodeError:
        return {"count": 0, "jobs": []}


def get_sessions_info() -> Dict[str, Any]:
    if not SESSIONS_DIR.exists():
        return {
            "count": 0,
            "messages": 0,
            "latest": None,
            "status": "idle",
            "active_sessions": 0,
            "thinking_sessions": 0,
            "details": [],
        }

    now = datetime.now()
    latest_time = None
    latest_role = None
    total_messages = 0
    thinking_sessions = 0
    active_sessions = 0
    session_count = 0
    details: list[Dict[str, Any]] = []

    for session_file in SESSIONS_DIR.glob("*.jsonl"):
        session_count += 1
        try:
            lines = session_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        messages = [l for l in lines if l.strip()]
        total_messages += len(messages)

        if not messages:
            details.append({
                "id": session_file.stem,
                "messages": 0,
                "latest": None,
            })
            continue

        try:
            last = json.loads(messages[-1])
        except json.JSONDecodeError:
            continue

        ts = last.get("timestamp") or last.get("time") or last.get("created_at")
        role = last.get("role")

        if not ts:
            continue

        try:
            msg_time = (
                datetime.fromtimestamp(ts)
                if isinstance(ts, (int, float))
                else datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            )
        except ValueError:
            continue

        if latest_time is None or msg_time > latest_time:
            latest_time = msg_time
            latest_role = role

        diff = (now - msg_time).total_seconds()

        if role == "user" and diff < 300:
            active_sessions += 1
            if diff < 30:
                thinking_sessions += 1

        details.append({
            "id": session_file.stem,
            "messages": len(messages),
            "latest": msg_time.isoformat(),
        })

    status = "idle"
    if latest_time:
        diff = (now - latest_time).total_seconds()
        if latest_role == "user":
            status = "thinking" if diff < 30 else "processing"
        elif latest_role == "assistant" and diff < 60:
            status = "active"

    if thinking_sessions:
        status = "thinking"

    details_sorted = sorted(details, key=lambda d: d["latest"] or "", reverse=True)[:20]

    return {
        "count": session_count,
        "messages": total_messages,
        "latest": latest_time.isoformat() if latest_time else None,
        "status": status,
        "active_sessions": active_sessions,
        "thinking_sessions": thinking_sessions,
        "details": details_sorted,
    }

def get_tailscale_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {"online": False, "ip": None, "hostname": None, "url": None}
    try:
        ip4 = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        if ip4.returncode == 0:
            ips = [l.strip() for l in ip4.stdout.splitlines() if l.strip()]
            info["ip"] = ips[0] if ips else None
    except Exception:
        pass
    try:
        stat = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=3)
        if stat.returncode == 0:
            data = json.loads(stat.stdout)
            self_node = data.get("Self", {})
            info["hostname"] = self_node.get("DNSName") or self_node.get("HostName")
            info["online"] = True
    except Exception:
        pass
    try:
        # Check funnel status
        funnel = subprocess.run(["tailscale", "funnel", "status"], capture_output=True, text=True, timeout=2)
        if funnel.returncode == 0:
            # Output example:
            # # Funnel on:
            # https://example.ts.net
            for line in funnel.stdout.splitlines():
                line = line.strip()
                if line.startswith("https://"):
                    info["url"] = line
                    break
    except Exception:
        pass
    return info

def ensure_avatar():
    # Avatar is now handled by manual download or install script
    pass

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.route("/")
def index():
    if not check_tailscale_auth():
        return "Tailscale認証が必要です。", 403
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    if not check_tailscale_auth():
        return jsonify({"error": "Tailscale認証が必要です"}), 403

    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "process": cache.get("process", 5, get_nanobot_process_info),
        "config": cache.get("config", 10, get_nanobot_config),
        "cron_jobs": cache.get("cron", 10, get_cron_jobs),
        "sessions": cache.get("sessions", 5, get_sessions_info),
        "tailscale": cache.get("tailscale", 5, get_tailscale_info),
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/sw.js")
def service_worker():
    return send_from_directory(PROJECT_DIR, "sw.js", mimetype="application/javascript")

# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=os.getenv("FLASK_RELOAD", "false").lower() == "true",
    )
