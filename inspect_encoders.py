#!/usr/bin/env python
"""Inspect the label encoders file"""
import joblib
from pathlib import Path

encoder_path = Path('trained_models') / "advanced_label_encoders.pkl"
print(f"File exists: {encoder_path.exists()}")
print(f"File size: {encoder_path.stat().st_size if encoder_path.exists() else 'N/A'}")

try:
    data = joblib.load(encoder_path)
    print(f"Type: {type(data)}")
    print(f"Contents: {data}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
except Exception as e:
    print(f"Error loading: {e}")
    import traceback
    traceback.print_exc()
