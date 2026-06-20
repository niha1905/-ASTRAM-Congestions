"""
Simple retraining script that ingests post-event feedback and updates lightweight
model adjustment weights stored under `trained_models/weights.json`.

This script is intentionally simple for demo purposes: it reads `backend/feedback.json`,
computes small scalar adjustments per model based on feedback, and writes the updated
weights. Run manually after collecting some feedback.
"""
from pathlib import Path
import json
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def load_feedback(feedback_path: Path):
    if not feedback_path.exists():
        return []
    try:
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception:
        # fallback: try pandas if available
        try:
            import pandas as pd
            df = pd.read_json(feedback_path)
            return df.to_dict(orient='records')
        except Exception:
            return []


def load_weights(weights_path: Path):
    if not weights_path.exists():
        return {}
    try:
        with open(weights_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_weights(weights_path: Path, weights: dict):
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    with open(weights_path, 'w', encoding='utf-8') as f:
        json.dump(weights, f, indent=2)


def compute_adjustments(feedback_records):
    """Compute simple adjustments from feedback.

    Rules (toy demo):
    - Increase `incident_volume_forecaster` weight by 0.01 * actual_incidents
    - Increase `road_closure_predictor` weight by 0.001 * actual_congestion_duration_min
    - Cap increments to avoid runaway changes
    """
    adj = {}
    for r in feedback_records:
        incidents = int(r.get('actual_incidents') or 0)
        duration = int(r.get('actual_congestion_duration_min') or 0)

        adj['incident_volume_forecaster'] = adj.get('incident_volume_forecaster', 0.0) + min(0.1, incidents * 0.01)
        adj['road_closure_predictor'] = adj.get('road_closure_predictor', 0.0) + min(0.05, duration * 0.001)

    return adj


def apply_adjustments(weights: dict, adjustments: dict):
    for k, v in adjustments.items():
        weights[k] = round(weights.get(k, 1.0) + v, 5)
    return weights


def main():
    base = Path(__file__).resolve().parent
    fb_path = base / 'feedback.json'
    weights_path = base.parent / 'trained_models' / 'weights.json'

    feedback = load_feedback(fb_path)
    if not feedback:
        print('No feedback found at', fb_path)
        return

    adjustments = compute_adjustments(feedback)
    weights = load_weights(weights_path)
    new_weights = apply_adjustments(weights, adjustments)
    save_weights(weights_path, new_weights)

    print('Applied adjustments:', adjustments)
    print('New weights saved to', weights_path)

    # Optional: run auxiliary maintenance tasks: train duration classifier and run audits
    try:
        # run training script (does nothing if data missing)
        script = base / 'tools' / 'train_duration_classifier.py'
        if script.exists():
            print('Running duration classifier training...')
            subprocess.check_call([sys.executable, str(script)])

        audit = base / 'tools' / 'audit_models.py'
        if audit.exists():
            print('Running model leakage audit...')
            subprocess.check_call([sys.executable, str(audit)])
    except Exception as e:
        logger.warning(f'Post-retrain auxiliary scripts failed: {e}')
if __name__ == '__main__':
    main()
