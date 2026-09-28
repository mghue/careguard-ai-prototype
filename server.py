#!/usr/bin/env python3
"""CareGuard synthetic end-to-end prototype server.

Serves the browser application, produces changing synthetic vitals, applies a
transparent decision engine, and persists events/alerts in SQLite.
"""

from __future__ import annotations

import json
import mimetypes
import random
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "careguard.db"
LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@dataclass
class PatientState:
    patient_id: str = "patient-demo-001"
    name: str = "Eleanor Morgan"
    age: int = 76
    room: str = "204"
    systolic: int = 132
    diastolic: int = 82
    glucose: int = 108
    heart_rate: int = 74
    spo2: int = 97
    hypertension: bool = True
    diabetes: bool = False
    afib: bool = False
    previous_stroke: bool = False
    heart_disease: bool = False
    smoking: bool = False
    status: str = "normal"
    status_title: str = "No warning signs detected"
    status_detail: str = "Synthetic monitoring is active."
    confidence: str = "92%"
    scenario: str = "normal"
    updated_at: str = ""


STATE = PatientState(updated_at=utc_now())


def init_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL,
              detail TEXT NOT NULL, event_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL,
              detail TEXT NOT NULL, urgency TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS readings (
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
              systolic INTEGER, diastolic INTEGER, glucose INTEGER,
              heart_rate INTEGER, spo2 INTEGER
            );
            """
        )


def add_event(title: str, detail: str, event_type: str = "info") -> None:
    with db() as connection:
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), utc_now(), title, detail, event_type),
        )


def add_alert(title: str, detail: str, urgency: str = "high") -> None:
    alert_id = str(uuid.uuid4())
    now = utc_now()
    with db() as connection:
        connection.execute(
            "INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?)",
            (alert_id, now, title, detail, urgency, "Open"),
        )
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), now, title, detail, "danger"),
        )


def rows(query: str, params: tuple = ()) -> list[dict]:
    with db() as connection:
        return [dict(row) for row in connection.execute(query, params).fetchall()]


def context_score() -> str:
    score = int(STATE.age >= 65)
    score += int(STATE.systolic >= 140 or STATE.diastolic >= 90)
    score += int(STATE.glucose >= 126)
    score += sum(
        map(int, [STATE.hypertension, STATE.diabetes, STATE.afib,
                  STATE.previous_stroke, STATE.heart_disease, STATE.smoking])
    )
    return "High context" if score >= 5 else "Moderate context" if score >= 3 else "Low context"


def snapshot() -> dict:
    with LOCK:
        patient = asdict(STATE)
    patient["risk_context"] = context_score()
    patient["synthetic"] = True
    patient["disclaimer"] = "Research prototype only; not a medical diagnosis."
    return {
        "patient": patient,
        "events": rows("SELECT * FROM events ORDER BY created_at DESC LIMIT 20"),
        "alerts": rows("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 20"),
        "readings": rows("SELECT * FROM readings ORDER BY id DESC LIMIT 24")[::-1],
        "server_time": utc_now(),
    }


SCENARIOS = {
    "normal": ("normal", "No warning signs detected", "Synthetic normal activity completed.", "92%", "info"),
    "instability": ("warning", "Instability detected", "Unsteady movement requires observation.", "78%", "warning"),
    "face": ("warning", "Possible facial weakness", "Synthetic facial-asymmetry sign detected.", "76%", "warning"),
    "arm": ("warning", "Possible arm weakness", "Synthetic arm-drift sign detected.", "81%", "warning"),
    "fall": ("emergency", "Possible fall detected", "Awaiting a response from the monitored person.", "93%", "danger"),
    "multiple": ("emergency", "Multiple possible stroke warning signs", "Synthetic face and arm signs require immediate human assessment.", "89%", "danger"),
}


def run_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise ValueError("Unknown scenario")
    level, title, detail, confidence, event_type = SCENARIOS[name]
    with LOCK:
        STATE.scenario = name
        STATE.status = level
        STATE.status_title = title
        STATE.status_detail = detail
        STATE.confidence = confidence
        STATE.updated_at = utc_now()
        if name == "instability":
            STATE.heart_rate = 88
        elif name in {"fall", "multiple"}:
            STATE.heart_rate = 96
        elif name == "normal":
            STATE.heart_rate = 74
    add_event(title, detail, event_type)
    if name == "multiple":
        add_alert("Multiple possible stroke signs", "Synthetic FAST evidence: face asymmetry and arm drift")
    return snapshot()


def simulation_loop() -> None:
    while True:
        time.sleep(3)
        with LOCK:
            STATE.systolic = max(105, min(170, STATE.systolic + random.choice([-1, 0, 0, 1])))
            STATE.diastolic = max(60, min(105, STATE.diastolic + random.choice([-1, 0, 0, 1])))
            STATE.glucose = max(75, min(190, STATE.glucose + random.choice([-1, 0, 0, 1])))
            baseline = 96 if STATE.scenario in {"fall", "multiple"} else 88 if STATE.scenario == "instability" else 74
            STATE.heart_rate = max(55, min(125, baseline + random.choice([-2, -1, 0, 1, 2])))
            STATE.spo2 = max(92, min(100, STATE.spo2 + random.choice([-1, 0, 0, 0, 1])))
            STATE.updated_at = utc_now()
            reading = (STATE.updated_at, STATE.systolic, STATE.diastolic, STATE.glucose, STATE.heart_rate, STATE.spo2)
        with db() as connection:
            connection.execute("INSERT INTO readings(created_at,systolic,diastolic,glucose,heart_rate,spo2) VALUES (?,?,?,?,?,?)", reading)
            connection.execute("DELETE FROM readings WHERE id NOT IN (SELECT id FROM readings ORDER BY id DESC LIMIT 200)")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def json_response(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/state":
            self.json_response(snapshot())
            return
        if route == "/api/health":
            self.json_response({"ok": True, "service": "careguard", "synthetic": True, "time": utc_now()})
            return
        super().do_GET()

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        try:
            payload = self.read_json()
            if route == "/api/scenario":
                self.json_response(run_scenario(payload.get("scenario", "normal")))
            elif route == "/api/health-context":
                allowed = {field for field in asdict(STATE) if field not in {"patient_id", "name", "room", "status", "status_title", "status_detail", "confidence", "scenario", "updated_at"}}
                with LOCK:
                    for key, value in payload.items():
                        if key in allowed:
                            setattr(STATE, key, value)
                    STATE.updated_at = utc_now()
                add_event("Health context updated", f"{context_score()}; background context only", "info")
                self.json_response(snapshot())
            elif route == "/api/alerts":
                add_alert(payload.get("title", "Test caregiver alert"), payload.get("detail", "Synthetic system test"), payload.get("urgency", "test"))
                self.json_response(snapshot(), HTTPStatus.CREATED)
            elif route.startswith("/api/alerts/"):
                alert_id = route.rsplit("/", 1)[-1]
                status = payload.get("status")
                if status not in {"Acknowledged", "Resolved"}:
                    raise ValueError("Invalid alert status")
                with db() as connection:
                    connection.execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))
                self.json_response(snapshot())
            elif route == "/api/respond":
                response = payload.get("response")
                if response == "okay":
                    run_scenario("normal")
                    add_event("Person responded", "Fall check dismissed by monitored person", "info")
                elif response == "help":
                    add_alert("Help requested", "Monitored person requested caregiver assistance")
                    with LOCK:
                        STATE.status = "emergency"
                        STATE.status_title = "Caregiver assistance requested"
                        STATE.status_detail = "A synthetic caregiver alert was generated."
                        STATE.confidence = "Confirmed"
                else:
                    raise ValueError("Invalid response")
                self.json_response(snapshot())
            elif route == "/api/reset":
                with db() as connection:
                    connection.execute("DELETE FROM alerts")
                    connection.execute("DELETE FROM events")
                    connection.execute("DELETE FROM readings")
                with LOCK:
                    fresh = PatientState(updated_at=utc_now())
                    STATE.__dict__.update(fresh.__dict__)
                self.json_response(snapshot())
            else:
                self.json_response({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    init_db()
    thread = threading.Thread(target=simulation_loop, daemon=True)
    thread.start()
    server = ThreadingHTTPServer(("127.0.0.1", 8080), Handler)
    print("CareGuard running at http://127.0.0.1:8080")
    print("Synthetic data is enabled. This prototype is not a medical device.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
