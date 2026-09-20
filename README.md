# DeepDetect

**A prototype AI-powered deepfake detection system.** Upload an image or video, get a
detection verdict with a confidence breakdown, and browse a history of past analyses —
built as a college project (B.Tech CSE) with an eye toward Smart India Hackathon-style
presentation.

> **Where this stands right now:** the full pipeline is real and working end to end —
> real file upload and validation, a real Flask API, and real image-forensics analysis
> that actually reads the uploaded pixels. What it is *not*, yet, is a trained,
> validated machine-learning model. See [Current limitations](#current-limitations)
> before presenting this as more than it is.

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [API reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Current limitations](#current-limitations)
- [Possible future improvements](#possible-future-improvements)
- [Team](#team)

## Features

- Drag-and-drop or click-to-upload for images (JPG/JPEG/PNG/WEBP, up to 15 MB) and
  videos (MP4/AVI/MOV/MKV, up to 100 MB), with live preview
- Client-side *and* server-side validation of file type and size (client-side checks
  are trivially bypassed, so the server never trusts them blindly)
- A step-by-step analysis animation (Upload → Preprocessing → AI Analysis →
  Classification → Result) while the real request is in flight
- A results card with verdict, confidence, and a real/deepfake probability breakdown
- Detection history, persisted per-browser via `localStorage`, with search-by-filename
  and filter-by-type
- A dark, glassmorphism-styled, keyboard-accessible, responsive UI with no external
  icon or font-hosting dependency beyond Google Fonts
- A real backend API doing real forensic analysis on the actual uploaded pixels — no
  fabricated numbers anywhere in the pipeline

## Tech stack

**Frontend:** vanilla HTML/CSS/JavaScript — no framework, no build step. `config.js`
holds the one setting (the backend URL) that changes between local development and a
real deployment.

**Backend:** Flask, with `gunicorn` for production. CORS is hand-rolled (a few lines in
`app.py`) rather than pulling in `flask-cors`, since a plain `multipart/form-data` POST
— what this frontend sends — doesn't trigger a browser preflight request anyway.

**Detection:** OpenCV, NumPy, and Pillow implementing two classical image-forensics
checks — Error Level Analysis and noise/sharpness-consistency analysis — described in
full in `backend/models/detector.py`'s own docstring, along with exactly why this is
what got built instead of a trained neural network (short version: no GPU, no labeled
dataset, and no network access to a pretrained model in the environment this was built
in — see that file for the complete reasoning).

## Project structure

```
deepdetect/
  index.html, style.css, script.js   Frontend
  config.js                           Deployment config (backend URL)
  backend/
    app.py                            Entry point, CORS, config, health check
    routes/detection.py               POST /api/detect/image, /api/detect/video
    models/detector.py                The forensics detector (see its docstring)
    services/                         Thin per-media-type wrappers around the detector
    utils/preprocessing.py            Shared image/video preprocessing helpers
    uploads/                          Where uploaded files land
    requirements.txt, Procfile        Dependencies and production start command
  tests/
    backend/test_api.py               unittest + Flask's test client
    frontend/run-tests.js             Playwright regression suite
    README.md                         How to run both
```

## Getting started

### Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The API comes up at `http://localhost:5000` (override with the `PORT` environment
variable). `app.py`'s own docstring documents every configuration variable it reads.

### Frontend

From the project root, serve the folder with any static file server — for example:

```bash
python -m http.server 5500
```

Then open `http://localhost:5500`. If the backend isn't running, the page says so
clearly on load rather than failing silently the first time you click Analyze.

### Both together

Frontend and backend are independent processes — run both of the commands above at the
same time, in two terminals, for the full app to work.

## API reference

### `POST /api/detect/image` · `POST /api/detect/video`

Multipart form upload, field name `file`.

**200 response:**

```json
{
  "prediction": "deepfake",
  "confidence": 0.947,
  "real_probability": 0.053,
  "deepfake_probability": 0.947,
  "message": "Compression and noise-consistency checks found localized irregularities. A face was detected in the analyzed frame(s)."
}
```

**Error responses** (`{"error": "..."}`):

| Status | Meaning |
|---|---|
| 400 | No file sent, or the wrong file type for that endpoint |
| 413 | File larger than the endpoint's size cap |
| 422 | File extension was valid but the content couldn't be decoded |

### `GET /`

Health check — `{"status": "ok", "service": "DeepDetect API", "endpoints": [...]}`.

## Testing

Two independent regression suites — see **[`tests/README.md`](tests/README.md)** for
full instructions:

```bash
# Backend — no server needs to be running
cd tests/backend && python -m unittest test_api.py -v

# Frontend — needs both servers already running (see tests/README.md)
cd tests/frontend && npm install && npm test
```

## Deployment

**Backend:** the included `Procfile` (`web: gunicorn app:app --bind 0.0.0.0:$PORT`) is
the convention platforms like Render, Railway, and Heroku auto-detect. `app.py` reads
`PORT`, `FLASK_DEBUG`, `ALLOWED_ORIGIN`, `UPLOAD_FOLDER`, and
`MAX_CONTENT_LENGTH_BYTES` from the environment, so the same code runs locally and in
production without edits — see its docstring for what each one does. `FLASK_DEBUG`
defaults to **off**, since Flask's interactive debugger lets anyone who reaches it run
arbitrary code, and that default matters the moment this is reachable from outside your
own machine.

**Frontend:** since it's static files with no build step, any static host works
(GitHub Pages, Netlify, Vercel, or similar). After deploying the backend, update the one
value in `config.js` to point at its real URL.

## Current limitations

Worth being upfront about, especially before presenting this to judges or a professor:

- **The detector is classical computer vision, not machine learning.** No neural
  network, no training data, and no accuracy validation against any labeled real/fake
  dataset — see `backend/models/detector.py` for the full reasoning and exactly what
  signals it actually checks.
- **Detection history is per-browser**, stored in `localStorage`, not synced to the
  server or shared across devices.
- **No authentication** — this is a single-user prototype.
- **Uploaded files persist on disk** in `backend/uploads/` and are never automatically
  cleaned up.

## Possible future improvements

- Swap `models/detector.py`'s internals for a real trained model — `predict_image()` /
  `predict_video()` and the response shape are already the stable interface the rest of
  the app depends on, by design, for exactly this swap
- A labeled dataset and an actual accuracy evaluation, however the detector ends up
  implemented
- Server-side history (a real database) instead of per-browser `localStorage`
- Batch upload / analyze multiple files at once
- Basic auth if this ever needs to be multi-user

## Team

*Add your team's names and roles here.*

## License

*Add a license here if your institution or hackathon requires one — MIT is a common
default for an open student project if you don't already have a preference.*
