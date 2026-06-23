"""Train a duration classifier by bucketing raw duration into categories.

Usage:
    python train_duration_classifier.py

This script expects the anonymized dataset CSV to be available at the
workspace root (file name detected automatically). It produces:
 - trained_models/duration_classifier.pkl
 - trained_models/duration_classifier_metrics.json

The script uses a time-based train/test split (by event date) to avoid leakage.
"""
from pathlib import Path
import json
import sys
import warnings
import logging

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib


def find_dataset():
    base = Path(__file__).resolve().parents[2]
    # try common filename in repo root
    candidates = list(base.glob('Astram*anonymized*.csv'))
    return candidates[0] if candidates else None


def bucket_duration_minutes(mins: float) -> str:
    if mins <= 30:
        return '<30'
    if mins <= 90:
        return '30-90'
    return '>90'


def main():
    ds = find_dataset()
    out_dir = Path(__file__).resolve().parents[1] / 'trained_models'
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ds:
        logger.info('Dataset not found in repo root; skipping training.')
        return
    logger.info('Loading dataset: %s', ds)
    df = pd.read_csv(ds)

    # Build duration from available timestamps when no explicit duration column exists
    if 'duration_min' in df.columns:
        df['duration_min'] = pd.to_numeric(df['duration_min'], errors='coerce')
    else:
        df['start_datetime'] = pd.to_datetime(df.get('start_datetime', df.get('created_date')), errors='coerce')
        df['end_datetime'] = pd.to_datetime(df.get('end_datetime', df.get('closed_datetime')), errors='coerce')
        df['duration_min'] = (df['end_datetime'] - df['start_datetime']).dt.total_seconds() / 60

    df = df.dropna(subset=['duration_min'])
    if df['duration_min'].empty:
        logger.info('No valid duration values found; skipping training.')
        return

    df['duration_bucket'] = df['duration_min'].apply(bucket_duration_minutes)

    # Features: use timestamp-based and event context features
    X = pd.DataFrame()
    X['hour'] = pd.to_datetime(df.get('start_datetime'), errors='coerce').dt.hour.fillna(12).astype(int)
    X['weekday'] = pd.to_datetime(df.get('start_datetime'), errors='coerce').dt.weekday.fillna(0).astype(int)
    X['month'] = pd.to_datetime(df.get('start_datetime'), errors='coerce').dt.month.fillna(1).astype(int)

    for col in ('event_type', 'event_cause', 'type', 'category'):
        if col in df.columns:
            X['event_type_code'] = df[col].fillna('unknown').astype('category').cat.codes
            break

    for col in ('priority', 'corridor', 'zone'):
        if col in df.columns:
            X[col] = df[col].fillna('Unknown').astype('category').cat.codes

    if 'title' in df.columns:
        X['title_len'] = df['title'].astype(str).str.len().fillna(0)

    y = df['duration_bucket']

    # Time-based split: sort by time_col (if available) and split
    if time_col and df[time_col].notna().any():
        df_sorted = df.sort_values(by=time_col)
        split_idx = int(len(df_sorted) * 0.8)
        X_train = X.loc[df_sorted.index[:split_idx]]
        y_train = y.loc[df_sorted.index[:split_idx]]
        X_test = X.loc[df_sorted.index[split_idx:]]
        y_test = y.loc[df_sorted.index[split_idx:]]
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    report = classification_report(y_test, preds, output_dict=True)

    model_path = out_dir / 'incident_duration_predictor_lgbm.pkl'
    metrics_path = out_dir / 'duration_classifier_metrics.json'
    artifact = {
        'model': clf,
        'features': list(X.columns),
        'duration_labels': ['<30', '30-90', '>90'],
        'label_to_minutes': {'<30': 20, '30-90': 60, '>90': 120},
        'description': 'Duration classifier trained on event timestamps from the provided dataset.',
    }
    joblib.dump(artifact, model_path)

    metrics = {'accuracy': float(acc), 'report': report}
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    summary_path = out_dir / 'advanced_models_summary.json'
    summary = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding='utf-8') or '{}')

    summary['duration_predictor'] = {
        'artifact': model_path.name,
        'metrics': metrics,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    logger.info('Trained duration classifier saved to %s', model_path)
    logger.info('Metrics written to %s', metrics_path)
    logger.info('Updated model summary at %s', summary_path)


if __name__ == '__main__':
    main()
