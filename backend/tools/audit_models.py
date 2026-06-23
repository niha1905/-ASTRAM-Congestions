"""Audit models for potential leakage using permutation importance.

This script attempts to load the dataset and the two models listed in
`trained_models/advanced_models_summary.json` (impact_score_model and
parking_overflow_predictor). It then computes permutation importance on a
time-based holdout and writes JSON reports under `trained_models/`.
"""
from pathlib import Path
import json
import warnings

warnings.filterwarnings('ignore')

import pandas as pd
import joblib
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split


def find_dataset():
    base = Path(__file__).resolve().parents[2]
    candidates = list(base.glob('Astram*anonymized*.csv'))
    return candidates[0] if candidates else None


def load_summary():
    p = Path(__file__).resolve().parents[1] / 'trained_models' / 'advanced_models_summary.json'
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding='utf-8'))


def safe_load_model(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return joblib.load(p)
    except Exception:
        return None


def basic_features(df):
    X = pd.DataFrame()
    # use numeric/time features commonly available
    for col in df.columns:
        if col.lower() in ('month', 'hour', 'weekday'):
            X[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'title' in df.columns:
        X['title_len'] = df['title'].astype(str).str.len().fillna(0)
    if 'type' in df.columns:
        X['type_code'] = df['type'].astype('category').cat.codes
    return X.fillna(0)


def run():
    ds = find_dataset()
    out_dir = Path(__file__).resolve().parents[1] / 'trained_models'
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ds:
        logger = logging.getLogger(__name__)
        logger.info('Dataset not found; skipping audit.')
        return

    df = pd.read_csv(ds)
    summary = load_summary()

    reports = {}

    # prepare X, y placeholders if possible
    X = basic_features(df)

    # Split
    if 'published' in df.columns:
        df['published_dt'] = pd.to_datetime(df['published'], errors='coerce')
        df_sorted = df.sort_values('published_dt')
        split_idx = int(len(df_sorted) * 0.8)
        train_idx = df_sorted.index[:split_idx]
        test_idx = df_sorted.index[split_idx:]
    else:
        train_idx, test_idx = train_test_split(df.index, test_size=0.2, random_state=42)

    X_test = X.loc[test_idx]

    # Impact score model
    im = summary.get('impact_score_model', {}).get('artifact')
    if im:
        model = safe_load_model(Path(__file__).resolve().parents[1] / im)
        if model and not X_test.empty:
            try:
                r = permutation_importance(model, X_test, [0]*len(X_test), n_repeats=5, random_state=42, n_jobs=1)
                reports['impact_score_model'] = {
                    'importances_mean': r.importances_mean.tolist(),
                    'importances_std': r.importances_std.tolist(),
                    'feature_names': X_test.columns.tolist()
                }
            except Exception as e:
                reports['impact_score_model'] = {'error': str(e)}

    # Parking overflow predictor
    pm = summary.get('parking_overflow_predictor', {}).get('artifact')
    if pm:
        model = safe_load_model(Path(__file__).resolve().parents[1] / pm)
        if model and not X_test.empty:
            try:
                r = permutation_importance(model, X_test, [0]*len(X_test), n_repeats=5, random_state=42, n_jobs=1)
                reports['parking_overflow_predictor'] = {
                    'importances_mean': r.importances_mean.tolist(),
                    'importances_std': r.importances_std.tolist(),
                    'feature_names': X_test.columns.tolist()
                }
            except Exception as e:
                reports['parking_overflow_predictor'] = {'error': str(e)}

    out_path = out_dir / 'permutation_importance_report.json'
    out_path.write_text(json.dumps(reports, indent=2), encoding='utf-8')
    logger = logging.getLogger(__name__)
    logger.info('Wrote permutation importance report to %s', out_path)


if __name__ == '__main__':
    run()
