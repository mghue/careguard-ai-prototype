# CareGuard AI Prototype

A browser-based research prototype for caregiver support. It demonstrates:

- Local webcam pose tracking with MediaPipe
- Transparent pose-based fall detection logic
- Guided FAST screening for face, arms, and speech
- Manual health context entry
- Deterministic alert fusion
- Synthetic presentation scenarios
- Simulated caregiver alert workflow

## Run

Python 3 is sufficient:

```bash
cd careguard-ai
python3 -m http.server 8080
```

Open `http://localhost:8080` in Chrome or Edge. Camera access requires localhost or HTTPS.

## Important limitations

This is a research and demonstration prototype—not a medical device. It does not diagnose or predict stroke. The FAST module screens for visible/audible warning signs, while health measurements provide background context only. MediaPipe assets are loaded from official public/CDN endpoints; the synthetic demo still works if model loading is unavailable.

## Recommended next phase

1. Replace prototype fall rules with a validated temporal pose model trained on URFD, FallVision, Pre-VFall, and representative older-adult data.
2. Replace the demonstration health score with a separately validated and calibrated risk model.
3. Add authenticated patient/caregiver accounts and encrypted storage.
4. Conduct clinician-supervised usability and performance evaluation.
