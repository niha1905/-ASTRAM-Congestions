# Model Cards — ASTRAM CongestionIQ

This document summarizes model artifacts, known issues, and recommended mitigations for judges and reviewers.

Summary
- `duration_predictor` (regression) — Known issue: extremely high MAE and negative R². A new duration *classifier* training script is provided at `backend/tools/train_duration_classifier.py`.
- `impact_score_model` — Very high reported R²; audit recommended to detect leakage. Use `backend/tools/audit_models.py` for a permutation-importance check.
- `parking_overflow_predictor` — Reported AUC == 1.0; indicates near-certain overfitting or leakage. Audit with `audit_models.py`.
- `scenario_perturbation_engine.json` — This is an explicit heuristic lookup. It is documented here and should be presented as a heuristic overlay in the UI.

How to run local checks

1. Install backend requirements:

```bash
python -m pip install -r backend/requirements.txt
```

2. Run duration classifier training (writes model & metrics):

```bash
python backend/tools/train_duration_classifier.py
```

3. Run permutation importance audit:

```bash
python backend/tools/audit_models.py
```

4. Run retrain with feedback and auxiliary tasks:

```bash
python backend/retrain_models.py
```

Report outputs are written to `backend/trained_models/`.

If you plan to submit, fix the duration predictor and remove target leakage before the judges inspect model logs.
