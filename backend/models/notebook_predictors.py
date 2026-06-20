"""
Prediction functions extracted from the ASTRAM notebook.
These functions load models and encoders from joblib and make predictions.
"""

import logging
import json
import numpy as np
import pandas as pd
from pathlib import Path
from .model_loader import model_loader

logger = logging.getLogger(__name__)


def predict_duration_minutes(event_cause, veh_type, corridor, hour, priority):
    """Predict incident duration in minutes (from notebook Model 5)"""
    try:
        artifact = model_loader.get_model('duration_predictor')
        if artifact is None or 'model' not in artifact:
            logger.warning("Duration predictor model not loaded")
            return 45.0  # Fallback
        
        row = pd.DataFrame([{
            "event_cause_enc": model_loader.encode_value(event_cause, "event_cause"),
            "veh_type_enc": model_loader.encode_value(veh_type, "veh_type"),
            "corridor_enc": model_loader.encode_value(corridor, "corridor"),
            "hour": int(hour),
            "priority_enc": model_loader.encode_value(priority, "priority"),
        }])
        
        prediction = artifact["model"].predict(row[artifact["features"]])[0]
        if isinstance(prediction, (bytes, bytearray)):
            prediction = prediction.decode('utf-8')

        if isinstance(prediction, str):
            prediction = float(artifact.get('label_to_minutes', {}).get(prediction, 45.0))
        else:
            prediction = float(prediction)

        if artifact.get("target_transform") == "log1p":
            prediction = float(np.expm1(prediction))
        return round(max(1.0, prediction), 1)
    except Exception as e:
        logger.error(f"Error in predict_duration_minutes: {e}")
        return 45.0


def predict_impact_score(event_cause, corridor, priority, hour, weekday, closure_probability):
    """Predict composite impact score (from notebook Model 6)"""
    try:
        artifact = model_loader.get_model('impact_score_model')
        if artifact is None or artifact.get('type') == 'fallback_heuristic':
            # Use heuristic fallback
            base_score = 50.0
            closure_factor = (closure_probability / 100.0) * 30
            return round(min(100, base_score + closure_factor), 1)
        
        if 'model' not in artifact:
            return 50.0
        
        encoders = model_loader.label_encoders
        hourly = artifact.get("hourly_volume", pd.DataFrame())
        
        matched = hourly[
            (hourly["corridor"].eq(str(corridor)))
            & (hourly["hour"].eq(int(hour)))
            & (hourly["weekday"].eq(int(weekday)))
        ] if not hourly.empty else pd.DataFrame()
        
        predicted_volume = float(matched["predicted_volume"].median()) if not matched.empty else 1.0
        criticality = float(artifact.get("corridor_criticality", {}).get(str(corridor), 0.25))
        
        row = pd.DataFrame([{
            "event_cause_enc": model_loader.encode_value(event_cause, "event_cause"),
            "corridor_enc": model_loader.encode_value(corridor, "corridor"),
            "priority_enc": model_loader.encode_value(priority, "priority"),
            "hour": int(hour),
            "weekday": int(weekday),
            "closure": int(float(closure_probability) >= 50),
            "predicted_volume": predicted_volume,
            "corridor_criticality": criticality,
        }])
        
        return round(float(np.clip(artifact["model"].predict(row[artifact["features"]])[0], 0, 100)), 1)
    except Exception as e:
        logger.error(f"Error in predict_impact_score: {e}")
        return 50.0


def predict_cascade_probability(corridor, event_cause, hour):
    """Predict congestion cascade probability (from notebook Model 7)"""
    try:
        artifact = model_loader.get_model('cascade_predictor')
        if artifact is None or artifact.get('type') == 'fallback_heuristic':
            return {
                "prob_30": 35.0,
                "prob_60": 55.0,
                "adjacent_corridors": []
            }
        
        if 'markov_table' not in artifact:
            return {"prob_30": 0.0, "prob_60": 0.0, "adjacent_corridors": []}
        
        table = artifact["markov_table"]
        matches = table[
            (table["corridor"].eq(str(corridor)))
            & (table["event_cause"].eq(str(event_cause)))
            & (table["hour"].eq(int(hour)))
        ]
        
        if matches.empty:
            matches = table[table["corridor"].eq(str(corridor))]
        
        if matches.empty:
            return {"prob_30": 0.0, "prob_60": 0.0, "adjacent_corridors": []}
        
        adjacency = artifact.get("adjacency", {})
        adjacent = [name for name, _ in adjacency.get(str(corridor), [])]
        
        return {
            "prob_30": round(float(matches["prob_30"].mean()) * 100, 1),
            "prob_60": round(float(matches["prob_60"].mean()) * 100, 1),
            "adjacent_corridors": adjacent,
        }
    except Exception as e:
        logger.error(f"Error in predict_cascade_probability: {e}")
        return {"prob_30": 0.0, "prob_60": 0.0, "adjacent_corridors": []}


def predict_parking_overflow(event_cause, corridor, hour, weekday, closure_probability):
    """Predict parking overflow probability (from notebook Model 8)"""
    try:
        artifact = model_loader.get_model('parking_overflow_predictor')
        if artifact is None or artifact.get('type') == 'fallback_heuristic':
            return 65.0 if closure_probability >= 50 else 35.0
        
        if 'model' not in artifact:
            return 50.0
        
        density = artifact.get("density_table", pd.DataFrame())
        matches = density[
            (density["event_cause"].eq(str(event_cause)))
            & (density["corridor"].eq(str(corridor)))
            & (density["hour"].eq(int(hour)))
        ] if not density.empty else pd.DataFrame()
        
        event_density = float(matches["event_density"].median()) if not matches.empty else 1.0
        
        row = pd.DataFrame([{
            "event_cause_enc": model_loader.encode_value(event_cause, "event_cause"),
            "corridor_enc": model_loader.encode_value(corridor, "corridor"),
            "hour": int(hour),
            "weekday": int(weekday),
            "event_density": event_density,
            "closure": int(float(closure_probability) >= 50),
        }])
        
        x = row[artifact["features"]]
        if artifact.get("scaler") is not None:
            x = artifact["scaler"].transform(x)
        
        probability = float(artifact["model"].predict_proba(x)[0, 1])
        return round(probability * 100, 1)
    except Exception as e:
        logger.error(f"Error in predict_parking_overflow: {e}")
        return 50.0


def green_corridor_path(origin_corridor, destination_corridor):
    """Find green corridor emergency path (from notebook Model 9)"""
    try:
        artifact = model_loader.get_model('green_corridor_pathfinder')
        if artifact is None or 'graph' not in artifact:
            return {"path": [], "total_weight": None, "signal_override_sequence": []}
        
        graph = artifact["graph"]
        origin = str(origin_corridor)
        destination = str(destination_corridor)
        
        if origin not in graph or destination not in graph:
            return {"path": [], "total_weight": None, "signal_override_sequence": []}
        
        # Dijkstra's algorithm
        unvisited = set(graph)
        distance = {node: float("inf") for node in graph}
        previous = {}
        distance[origin] = 0.0
        
        while unvisited:
            current = min(unvisited, key=lambda node: distance[node])
            unvisited.remove(current)
            if current == destination or distance[current] == float("inf"):
                break
            
            for edge in graph[current]:
                alt = distance[current] + float(edge["weight"])
                if alt < distance.get(edge["to"], float("inf")):
                    distance[edge["to"]] = alt
                    previous[edge["to"]] = current
        
        # Reconstruct path
        path = []
        node = destination
        while node in previous or node == origin:
            path.append(node)
            if node == origin:
                break
            node = previous[node]
        
        path = list(reversed(path)) if path and path[0] == destination else []
        
        return {
            "path": path,
            "total_weight": round(distance[destination], 2) if path else None,
            "signal_override_sequence": [f"Override signals on {name}" for name in path],
        }
    except Exception as e:
        logger.error(f"Error in green_corridor_path: {e}")
        return {"path": [], "total_weight": None, "signal_override_sequence": []}


def apply_scenario(base_package: dict, scenario_name: str):
    """Apply what-if scenario to predictions (from notebook Model 10)"""
    try:
        artifact = model_loader.get_model('scenario_engine')
        if artifact is None or 'scenarios' not in artifact:
            return base_package
        
        scenario = artifact["scenarios"].get(scenario_name)
        if scenario is None:
            logger.warning(f"Unknown scenario: {scenario_name}")
            return base_package
        
        adjusted = dict(base_package)
        
        if "duration_multiplier" in scenario and "estimated_duration_min" in adjusted:
            adjusted["estimated_duration_min"] = round(
                adjusted["estimated_duration_min"] * scenario["duration_multiplier"], 1
            )
        
        if "incident_volume_multiplier" in scenario and "predicted_incidents" in adjusted:
            adjusted["predicted_incidents"] = round(
                adjusted["predicted_incidents"] * scenario["incident_volume_multiplier"], 1
            )
        
        if "closure_probability_multiplier" in scenario and "closure_probability" in adjusted:
            adjusted["closure_probability"] = round(
                min(100, adjusted["closure_probability"] * scenario["closure_probability_multiplier"]), 1
            )
        
        adjusted["scenario_applied"] = scenario_name
        adjusted["scenario_factors"] = scenario
        
        return adjusted
    except Exception as e:
        logger.error(f"Error in apply_scenario: {e}")
        return base_package
