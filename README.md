# Model Workflow — Track A

This repository contains model code, training utilities, serving endpoints, and front-end integrations for the Track A project. This README describes the end-to-end model lifecycle: data, training, evaluation, deployment, monitoring, and how the app integrates ML predictions.

## Contents
- **Overview** — high-level architecture and responsibilities.
- **Data** — sources, storage, and preprocessing.
- **Modeling** — model types, training pipeline, and evaluation.
- **Serving** — inference, API endpoints, and frontend integration.
- **Retraining & CI** — how to retrain and schedule updates.
- **Monitoring & Metrics** — validation, drift detection, and alerts.
- **Files & References** — key files in this repo.
- **Quick Start** — local commands to run training and server.

## Overview

The ML components are structured to separate concerns between model logic, feature preparation, training orchestration, and serving. Backend Python modules host model loaders, predictors, and REST endpoints. Frontend components call the backend prediction APIs and render results in the UI.

Key directories:

- [backend](backend): Python service with model logic, routes, and utilities.
- [trained_models](trained_models): persisted model artifacts and summaries.
- [components/ml](components/ml) and [hooks](hooks): frontend components and hooks that consume model output.
- [lib](lib): client utilities and API wrappers used by frontend code.

## Data

Primary data sources and storage:

- Event and telemetry CSVs (archived under `archive/`).
- External APIs via [backend/mappls_client.py](backend/mappls_client.py).

Preprocessing:

- Scripts and functions in `backend/predictors.py` and `backend/model_loader.py` perform feature extraction and normalization.
- Persisted datasets for experiments can be placed in `archive/` and referenced by training scripts.

## Modeling

Model types and responsibilities:

- Short-lived heuristics and analytic functions live alongside ML code in `backend/predictors.py`.
- Advanced models and serializations are stored in `trained_models/` and summarized in `trained_models/advanced_models_summary.json`.

Training pipeline:

1. Prepare and clean data using the ETL helpers in `backend/predictors.py`.
2. Run training scripts (examples below) which produce serialized model artifacts and evaluation reports.

Example training scripts:

- [backend/retrain_models.py](backend/retrain_models.py) — higher-level orchestrator for retraining workflows.
- [backend/tools/train_duration_classifier.py](backend/tools/train_duration_classifier.py) — example classifier training utility.

Evaluation and metrics:

- Evaluation logic lives next to training code and writes metrics to JSON or logs.
- Use `backend/tools/check_model_metrics.py` to validate metrics and guard releases.

Versioning and artifacts:

- Store trained artifacts in `trained_models/` with clear naming that includes model type, dataset snapshot, and timestamp.
- Keep `trained_models/advanced_models_summary.json` in sync with production deployments.

## Serving & Inference

Serving architecture:

- Model loading and inference are handled by `backend/model_loader.py` and `backend/models/model_loader.py` (see `backend/models` for model-specific code).
- Prediction endpoints are exposed under `backend/routes/`, notably [backend/routes/predictions.py](backend/routes/predictions.py).

Integration with frontend:

- Frontend components and hooks that request predictions include [hooks/use-ml-predictions.ts](hooks/use-ml-predictions.ts) and UI pieces in [components/ml](components/ml).
- The frontend client wrappers live in [lib/ml-api-client.ts](lib/ml-api-client.ts) and [lib/api.ts](lib/api.ts).

Example request (curl):

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"event": {"latitude": 12.9, "longitude": 77.6, "timestamp": "2025-01-01T12:00:00Z"}}'
```

Or using the frontend client in code:

See [lib/ml-api-client.ts](lib/ml-api-client.ts) for JS/TS examples.

## Retraining & Continuous Training

When to retrain:

- Detectable performance degradation on production metrics.
- Data distribution shift or significant feature drift.
- New labeled data availability.

Retraining process:

1. Collect the latest labeled dataset and confirm data quality.
2. Run the training script (see `backend/retrain_models.py`).
3. Evaluate and compare metrics against the production baseline.
4. If improved, publish the artifact to `trained_models/` and update `advanced_models_summary.json`.
5. Deploy the new artifact and monitor.

Automation tips:

- Use CI to run reproducible training and validation jobs. Store intermediate artifacts and metrics in an artifact store or within `trained_models/` with immutable filenames.
- Automate canary rollout and A/B test of new models in production before full cutover.

## Monitoring & Metrics

What to track:

- Prediction latencies, error rates, and throughput.
- Model performance metrics over time (MAE, RMSE, accuracy, F1, depending on model).
- Input feature distributions to detect drift.

Tools in repo:

- [backend/tools/check_model_metrics.py](backend/tools/check_model_metrics.py) — scripts to check metric thresholds.
- Frontend health checks: see `components/ml/ml-health-check.tsx` and `components/ml/example-event-analysis.tsx` for UI hooks that surface model health.

Alerts & escalation:

- Wire metric failures to your monitoring/alerting system (PagerDuty, Slack, etc.) from your CI or monitoring jobs.

## Security & Privacy

- Remove or anonymize PII before using datasets for training; archived CSVs under `archive/` should be preprocessed accordingly.
- Enforce strict access controls for `trained_models/` and any artifact stores.

## Files & References

- Model loader: [backend/model_loader.py](backend/model_loader.py)
- Training orchestrator: [backend/retrain_models.py](backend/retrain_models.py)
- Predictors and feature code: [backend/predictors.py](backend/predictors.py)
- Routes: [backend/routes/predictions.py](backend/routes/predictions.py)
- Training tools: [backend/tools/train_duration_classifier.py](backend/tools/train_duration_classifier.py)
- Metrics check: [backend/tools/check_model_metrics.py](backend/tools/check_model_metrics.py)
- Frontend client: [lib/ml-api-client.ts](lib/ml-api-client.ts)
- Frontend hook: [hooks/use-ml-predictions.ts](hooks/use-ml-predictions.ts)
- Requirements: [backend/requirements.txt](backend/requirements.txt)
- Model artifacts dir: `trained_models/`

## Quick Start

1. Create a Python virtual environment and install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # use `.\\.venv\\Scripts\\activate` on Windows PowerShell
pip install -r backend/requirements.txt
```

2. Run the backend server locally (example):

```bash
# From repository root
python -m backend.__main__
```

3. Trigger training (example):

```bash
python backend/retrain_models.py --config configs/retrain_config.yaml
```

4. Call the prediction endpoint using `curl` or the frontend.

## Troubleshooting

- If a model fails to load, confirm the artifact path and compatibility with the loader in `backend/model_loader.py`.
- If predictions are slow, inspect serialization format (use joblib or optimized formats) and the inference hardware.
- If metrics degrade after deployment, roll back to the previous artifact and run `backend/tools/check_model_metrics.py`.

## Contributing

- Keep training code and model evaluation deterministic and version-controlled.
- Add unit tests for preprocessing and model I/O to avoid silent breakages.

---

If you'd like, I can also:

- Add a short `CONTRIBUTING.md` describing how to add a new model.
- Create example `configs/retrain_config.yaml` used by the retrain script.

File created: [README.md](README.md)
# ASTRAM CongestionIQ🚦 Predict traffic disruptions before they happen

ASTRAM is an AI-powered traffic intelligence platform that converts real-time news events into congestion forecasts, road closure predictions, diversion routes, and operational deployment recommendations for city traffic management teams.

# ASTRAM CongestionIQ — Detailed Project README

 Real-time event-driven traffic intelligence platform that ingests news and operational signals, predicts local traffic impact using an ensemble of ML models and graph algorithms, and produces actionable resource and routing recommendations for operators.



**Contents:**
- Project overview
- Architecture & data flow
- Component responsibilities and key files
- Local development & deployment (Render)
- ML model summary and retraining workflow
- Demo script and hackathon talking points
- Candidate files for removal (needs confirmation)

---

## 1. Project Overview

ASTRAM ingests public news sources, extracts event metadata (type, time window, location), maps events to a road network, and runs a suite of models to estimate incident counts, closure probabilities, hotspot risk, and recommended operational responses (officer counts, barricade placements, diversion routes). The system is designed for low-latency inference and operator-facing decision support.

Primary goals for the hackathon:
- Demonstrate end-to-end ingestion → prediction → operator recommendation pipeline
- Show interactive scenarios via the web dashboard and the Cascade Studio
- Highlight ML performance and explainability for key recommendations

---

## 2. Architecture & Data Flow

High-level flow:
- News Scraper (backend.scrapers.news_scraper.py) pulls RSS/news feeds and emits parsed event records.
- Event Normalization maps unstructured text to structured fields (type, time, approximate location).
- Geo-mapping converts place mentions to lat/lon and snaps them to the operational corridor map.
- ML Inference: the `backend/models` modules load serialized models and run predictions; outputs are normalized into a single JSON API shape.
- Routing: `backend/mappls_client.py` integrates Mappls APIs for route geometry and distance/duration estimates used in routing and corridor impact scoring.
- Frontend Dashboard (Next.js) polls the API and provides interactive visualizations and controls.

Key endpoints (backend/routes):
- `GET /api/health` — health check
- `GET /api/news` — recent parsed events
- `POST /api/predict` — run predictions for a given event (used by UI)
- `GET /api/mappls/token` — returns Mappls access token when needed by the frontend

Map services:
- Uses Mappls (MapmyIndia) routing and tiles. The backend prefers a REST/SDK key when available, falling back to OAuth client-credentials. See `backend/mappls_client.py` for token handling and polyline decoding.

---

## 3. Component Responsibilities & Key Files

- Frontend (Next.js app/):
    - `app/(app)/page.tsx` — main dashboard shell
    - `components/map/*` — map components and Mappls integration
    - `components/operations-suite/*` — operational views (briefs, scenario simulator)

- Backend (Flask backend/):
    - `backend/routes/*` — API blueprints
    - `backend/models/*` — model loaders and predictor wrappers
    - `backend/mappls_client.py` — routing helpers, polyline decoding, OAuth handling
    - `backend/retrain_models.py` — training orchestration and model dumps

- Models & Data:
    - `trained_models/` — serialized model artifacts (do not delete without archiving)
    - `components.json` — UI layout / component metadata used by the frontend

---

## 4. Local Development

Prereqs:
- NodeJS 18+ (pnpm or npm/yarn supported; repo includes `pnpm-lock.yaml`)
- Python 3.9–3.11

Backend (developer mode):

1. Create and activate a Python virtualenv in `backend/`:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the Flask backend (development):

```powershell
# from backend/
$env:FLASK_APP = 'backend'
$env:FLASK_ENV = 'development'
python -m flask run --port 5000
```

Frontend (developer mode):

```bash
# from project root
pnpm install
pnpm dev
# or npm install && npm run dev
```

Set environment variables in a `.env` file in the repo root (example below). The frontend uses `NEXT_PUBLIC_API_BASE_URL` to call the backend.

Environment example (repo root `.env`):

```env
MAPPLS_CLIENT_ID=
MAPPLS_CLIENT_SECRET=
MAPPLS_REST_API_KEY=
NEXT_PUBLIC_MAPPLS_REST_API_KEY=
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:5000/api
```

---

## 5. Deployment (Render.com)

We include a `render.yaml` manifest to deploy the frontend and backend as separate services. The manifest sets build/start commands and placeholder env vars used for production. See [render.yaml](render.yaml) for the canonical manifest used during the hackathon demo.

Basic Render steps summary:
1. Create a new Render service from the repo and import the `render.yaml` (Render will create two services: frontend and backend).
2. Set required environment variables in Render dashboard (Mappls keys, CORS_ORIGINS, etc.).
3. Deploy; both services will auto-deploy on git commit.

---

## 6. ML Models & Retraining

Where models live:
- `trained_models/` contains saved model artifacts and JSON metadata.

Training workflow (high level):
1. Prepare training CSVs via `backend/tools/*` or Jupyter notebooks.
2. Run `backend/retrain_models.py` which trains and writes joblib outputs to `trained_models/`.
3. Commit model metadata (not large binary files) and consider storing actual model binaries in an object store if collaborating.

Notes on reproducibility:
- Use pinned package versions in `backend/requirements.txt`.
- Tests and manual validation notebooks are in the repo; include model metrics in `docs/MODELS_README.md`.

---

## 7. Demo Script & Hackathon Talking Points (Step-by-step)

Demo duration: ~6–8 minutes

1. Elevator pitch (30s): explain problem, dataset, and what ASTRAM produces.
2. Live demo (3–4 min):
     - Show the dashboard and a current event from `GET /api/news`.
     - Run a scenario: open Cascade Studio, apply a +20k visitors perturbation, and show impact scores and recommended officer deployment.
     - Trigger a route calculation: demonstrate Mappls-backed route geometry (via `fetch_mappls_route`) and show suggested diversions.
3. ML explanation (1–2 min): briefly describe top-performing models, key features, and model validation metrics.
4. Operational value & next steps (30s): mention integration with city operations, adaptor for live sensor feeds, and improvements (real-time telemetry, privacy-safe telemetry storage).

Suggested slides and talking bullets:
- Problem statement + city impact
- Data sources and ETL pipeline
- ML ensemble architecture + metrics
- Live demo + UI walkthrough
- Limitations and future work

---

## 8. Candidate Files For Removal (please confirm before I delete)

I recommend we do NOT automatically delete anything without your confirmation. Below are files I think are likely unnecessary, large, or duplicates. Confirm which you want removed and I will delete them and update `.gitignore` as needed.

- `Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv` — looks like a duplicate/accidental export (likely large). Candidate for removal or moving to `archive/`.
- `ASTRAM_CongestionIQ_ML_SUBMISSION.ipynb` — if this is a submission notebook duplicate, consider archiving or removing.
- Any large artifacts accidentally checked in (e.g., big model binaries inside source folders). Leave `trained_models/` only after confirmation.

To remove a file locally (example):

```powershell
# from repo root
Remove-Item "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
# or move to archive
Move-Item "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv" archive\
```

---

## 9. Troubleshooting

- Mappls errors: ensure `MAPPLS_REST_API_KEY` or `MAPPLS_CLIENT_*` env vars are set; check `backend/mappls_client.py` logs.
- Model import issues: ensure `trained_models/` contains required artifacts and `requirements.txt` dependencies match the training environment.

---

## 10. Next Steps I can take for you

- Apply the file deletions you confirm and update `.gitignore`.
- Add a short `DEMO.md` with the exact commands and screenshots for judges.
- Create a minimal `presentation/` slide deck with the architecture mermaid diagram.

If you want me to delete the candidate files above, reply which ones to remove and I will perform the deletions.
