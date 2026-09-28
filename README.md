# CareGuard AI Prototype

A dependency-free, end-to-end research prototype for caregiver support. A Python backend generates synthetic patient readings, persists events in SQLite, applies transparent alert rules, and serves the browser dashboard.

It demonstrates:

- Local webcam pose tracking with MediaPipe
- Transparent pose-based fall detection logic
- Guided FAST screening for face, arms, and speech
- Manual health context entry
- Deterministic alert fusion
- Synthetic presentation scenarios
- Simulated caregiver alert workflow
- Continuously changing synthetic vital signs
- Persistent events and alerts backed by SQLite
- Alert acknowledgement and resolution
- REST endpoints for scenarios, health context, responses, and session reset

## Run

Python 3.10 or newer is sufficient. No packages need to be installed:

```bash
cd careguard-ai
python3 server.py
```

Open `http://127.0.0.1:8080` in Chrome or Edge. Camera access requires localhost or HTTPS.

The server creates `data/careguard.db` automatically. This local database is ignored by Git.

## End-to-end demo

1. Open the Command Center and watch the synthetic readings update.
2. Select **Instability** and confirm that the status and event timeline change.
3. Select **Fall detected**, then choose **I am okay** or **Request help**.
4. Select **Multiple FAST signs** to generate a caregiver alert.
5. Open **Alert Center** and acknowledge, then resolve, the alert.
6. Update the health form and confirm that the context score persists after refresh.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Service health check |
| `/api/state` | GET | Patient, readings, events, and alerts |
| `/api/scenario` | POST | Run a controlled synthetic scenario |
| `/api/health-context` | POST | Update synthetic health context |
| `/api/respond` | POST | Record a fall-check response |
| `/api/alerts` | POST | Create a simulated caregiver alert |
| `/api/alerts/{id}` | POST | Acknowledge or resolve an alert |
| `/api/reset` | POST | Reset the synthetic session |

## Important limitations

This is a research and demonstration prototype—not a medical device. It does not diagnose or predict stroke. The FAST module screens for visible/audible warning signs, while health measurements provide background context only. MediaPipe assets are loaded from official public/CDN endpoints; the synthetic demo still works if model loading is unavailable.

## Recommended next phase

1. Replace prototype fall rules with a validated temporal pose model trained on URFD, FallVision, Pre-VFall, and representative older-adult data.
2. Replace the demonstration health score with a separately validated and calibrated risk model.
3. Add authenticated patient/caregiver accounts and encrypted storage.
4. Conduct clinician-supervised usability and performance evaluation.
