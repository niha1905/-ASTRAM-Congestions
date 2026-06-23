"""Check model metrics and exit non-zero if thresholds violated.

Rules (can be adjusted):
 - duration predictor R2 must be >= 0 (no negative R2)
 - impact_score_model R2 must be <= 0.99 (extremely high values may indicate leakage)
 - parking_overflow_predictor AUC must be < 0.999 (perfect AUC flags leakage)
"""
import json
from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)


def main():
    base = Path(__file__).resolve().parents[1] / 'trained_models'
    summary_path = base / 'advanced_models_summary.json'
    if not summary_path.exists():
        logger.info('advanced_models_summary.json not found — skipping strict checks.')
        return 0

    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    exit_code = 0

    dur = summary.get('duration_predictor', {}).get('metrics', {})
    if dur.get('r2', 0) < 0:
        logger.error('duration_predictor R2 is negative: %s', dur.get('r2'))
        exit_code = 2

    impact = summary.get('impact_score_model', {}).get('metrics', {})
    if impact.get('r2', 0) > 0.99:
        logger.error('impact_score_model R2 suspiciously high: %s', impact.get('r2'))
        exit_code = 3

    parking = summary.get('parking_overflow_predictor', {}).get('metrics', {})
    if parking.get('auc', 0) >= 0.999:
        logger.error('parking_overflow_predictor AUC suspicious/perfect: %s', parking.get('auc'))
        exit_code = 4

    if exit_code == 0:
        logger.info('Model metric checks passed.')
    else:
        logger.warning('Model metric checks failed. See errors above.')

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
