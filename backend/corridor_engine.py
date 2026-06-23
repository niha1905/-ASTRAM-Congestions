"""
Dynamic corridor geometry and congestion scoring for the dashboard map.

Corridor anchors come from the green_corridor_pathfinder model centroids.
Road geometry is fetched from Mappls when available; congestion blends ML
predictions with active news/event impacts on each corridor.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from .mappls_client import fetch_mappls_route, is_mappls_configured
from .models.model_loader import model_loader
from .models.predictors import (
    CascadePredictor,
    ClosurePredictor,
    ImpactScorePredictor,
    IncidentVolumePredictor,
)
from .news_geo import _normalize_route_key

logger = logging.getLogger(__name__)

_path_cache: Dict[str, List[List[float]]] = {}

LOCALITY_TO_CORRIDOR: Dict[str, str] = {
    'koramangala': 'Hosur Road',
    'silk board': 'Hosur Road',
    'silk board junction': 'Hosur Road',
    'hosur road': 'Hosur Road',
    'indiranagar': 'CBD 2',
    'indiranagar 100ft road': 'CBD 2',
    'mg road': 'CBD 1',
    'brigade road': 'CBD 1',
    'whitefield': 'ORR East 1',
    'marathahalli': 'ORR East 1',
    'bellandur': 'ORR East 1',
    'electronic city': 'Hosur Road',
    'yelahanka': 'Airport New South Road',
    'hebbal': 'Bellary Road 1',
    'hebbal flyover': 'Bellary Road 1',
    'jayanagar': 'Bannerghata Road',
    'rajajinagar': 'West of Chord Road',
    'outer ring road': 'ORR East 1',
    'orr east 1': 'ORR East 1',
    'old airport road': 'Old Airport Road',
    'mysore road': 'Mysore Road',
    'tumkur road': 'Tumkur Road',
    'bannerghatta': 'Bannerghata Road',
    'bannerghatta road': 'Bannerghata Road',
}

CORRIDOR_ZONE: Dict[str, str] = {
    'Hosur Road': 'koramangala',
    'CBD 1': 'mg road',
    'CBD 2': 'indiranagar',
    'ORR East 1': 'whitefield',
    'Bellary Road 1': 'hebbal',
    'Bannerghata Road': 'jayanagar',
    'West of Chord Road': 'rajajinagar',
    'Airport New South Road': 'yelahanka',
    'Old Airport Road': 'indiranagar',
    'Mysore Road': 'mysore road',
    'Tumkur Road': 'tumkur road',
}


def _risk_status(congestion: int) -> str:
    if congestion > 75:
        return 'severe'
    if congestion > 50:
        return 'high'
    if congestion > 25:
        return 'moderate'
    return 'low'


def _hour_baseline(hour: int) -> float:
    if hour in (8, 9, 10, 17, 18, 19, 20):
        return 58.0
    if hour in (7, 11, 16, 21):
        return 42.0
    if hour in (0, 1, 2, 3, 4, 5):
        return 18.0
    return 32.0


def get_centroid_map() -> Dict[str, Tuple[float, float]]:
    artifact = model_loader.get_model('green_corridor_pathfinder')
    if not artifact or not isinstance(artifact, dict):
        return {}
    centroids = {}
    for entry in artifact.get('centroids', []):
        name = entry.get('corridor')
        lat = entry.get('latitude')
        lon = entry.get('longitude')
        if name and lat is not None and lon is not None and name != 'Non-corridor':
            centroids[name] = (float(lat), float(lon))
    return centroids


def map_text_to_corridor(text: str) -> Optional[str]:
    loc = str(text or '').lower().strip()
    if not loc:
        return None

    preset = {
        'stadium': 'CBD 2',
        'victoria': 'CBD 1',
        'expo': 'ORR East 1',
        'airport': 'Airport New South Road',
        'ring road': 'ORR East 1',
        'outer ring': 'ORR East 1',
    }
    for key, corridor in preset.items():
        if key in loc:
            return corridor

    matches = [k for k in LOCALITY_TO_CORRIDOR if k in loc]
    if matches:
        return LOCALITY_TO_CORRIDOR[max(matches, key=len)]

    centroids = get_centroid_map()
    for corridor in centroids:
        if corridor.lower() in loc or loc in corridor.lower():
            return corridor

    return None


def map_event_to_corridor(event: dict, matched_key: Optional[str] = None) -> str:
    if matched_key:
        route_key = _normalize_route_key(matched_key)
        if route_key and route_key in LOCALITY_TO_CORRIDOR:
            return LOCALITY_TO_CORRIDOR[route_key]

    traffic_plan = event.get('traffic_plan') or {}
    for field in ('affected', 'divert_to'):
        corridor = map_text_to_corridor(traffic_plan.get(field, ''))
        if corridor:
            return corridor

    news = event.get('news') or {}
    for field in ('location', 'title', 'summary'):
        corridor = map_text_to_corridor(news.get(field, ''))
        if corridor:
            return corridor

    corridor = map_text_to_corridor(event.get('name', ''))
    if corridor:
        return corridor

    position = event.get('position')
    if position and len(position) >= 2:
        return nearest_corridor(float(position[0]), float(position[1]))

    return 'CBD 2'


def nearest_corridor(lat: float, lon: float) -> str:
    centroids = get_centroid_map()
    if not centroids:
        return 'CBD 2'

    best_name = 'CBD 2'
    best_dist = float('inf')
    for name, (clat, clon) in centroids.items():
        dist = (lat - clat) ** 2 + (lon - clon) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def _offset_path(lat: float, lon: float) -> List[List[float]]:
    return [
        [lat, lon],
        [round(lat - 0.006, 6), round(lon + 0.004, 6)],
        [round(lat - 0.012, 6), round(lon + 0.009, 6)],
        [round(lat - 0.018, 6), round(lon + 0.014, 6)],
    ]


def _corridor_segment_endpoints(lat: float, lon: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Build a ~2 km segment through the corridor anchor for Mappls routing."""
    bearing_rad = math.radians(135)  # SE-ish, typical arterial direction in BLR maps
    d_lat = (1800 / 111_000) * math.cos(bearing_rad)
    d_lon = (1800 / (111_000 * math.cos(math.radians(lat)))) * math.sin(bearing_rad)
    origin = (lat, lon)
    destination = (round(lat - d_lat, 6), round(lon + d_lon, 6))
    return origin, destination


def build_corridor_path(
    corridor_name: str,
    centroid: Tuple[float, float],
    events: List[dict],
) -> List[List[float]]:
    if corridor_name in _path_cache:
        return _path_cache[corridor_name]

    for event in events:
        plan = event.get('traffic_plan') or {}
        path = plan.get('path')
        if isinstance(path, list) and len(path) >= 2:
            return [[float(p[0]), float(p[1])] for p in path]

    lat, lon = centroid
    origin, destination = _corridor_segment_endpoints(lat, lon)

    if is_mappls_configured():
        origin_str = f'{origin[0]},{origin[1]}'
        dest_str = f'{destination[0]},{destination[1]}'
        routed = fetch_mappls_route(origin_str, dest_str)
        if routed and len(routed) >= 2:
            _path_cache[corridor_name] = routed
            return routed

    fallback = _offset_path(lat, lon)
    _path_cache[corridor_name] = fallback
    return fallback


def compute_corridor_congestion(
    corridor_name: str,
    hour: int,
    weekday: int,
    month: int,
    events: List[dict],
) -> int:
    zone = CORRIDOR_ZONE.get(corridor_name, corridor_name)
    event_type = 'unplanned'

    closure = ClosurePredictor.predict(event_type, zone, corridor_name, 'Medium', hour, 45)
    closure_prob = float(closure.get('closure_probability', 0) or 0)

    impact = ImpactScorePredictor.predict(event_type, corridor_name, 'Medium', hour, weekday, closure_prob)
    impact_score = float(impact.get('impact_score', 0) or 0)

    volume = IncidentVolumePredictor.predict(zone, corridor_name, event_type, hour, weekday, month)
    volume_val = float(volume.get('prediction', 0) or 0)

    cascade = CascadePredictor.predict(corridor_name, event_type, hour)
    cascade_prob = float(cascade.get('prob_30', 0) or 0)

    score = (
        _hour_baseline(hour) * 0.40
        + closure_prob * 0.18
        + min(100.0, impact_score) * 0.12
        + min(35.0, volume_val * 1.5) * 0.10
        + min(20.0, cascade_prob * 100.0) * 0.08
    )

    event_boost = 0.0
    for event in events:
        priority = str(event.get('priority', 'Medium'))
        event_boost += 9 if priority.lower() == 'high' else 5
        plan = event.get('traffic_plan') or {}
        if str(plan.get('source', '')).startswith('mappls'):
            event_boost += 2

    score += min(28.0, event_boost)

    return min(95, max(12, int(round(score))))


def build_dynamic_corridors(
    events: List[dict],
    hour: int,
    weekday: int,
    month: int,
    *,
    max_corridors: int = 12,
) -> List[dict]:
    """Build corridor overlays with Mappls geometry and ML/event-weighted congestion."""
    centroids = get_centroid_map()
    if not centroids:
        return []

    corridor_events: Dict[str, List[dict]] = {name: [] for name in centroids}
    for event in events:
        corridor = map_event_to_corridor(event)
        if corridor in corridor_events:
            corridor_events[corridor].append(event)
        else:
            corridor_events.setdefault(corridor, []).append(event)

    active_names = set()
    for event in events:
        active_names.add(map_event_to_corridor(event))

    scored: List[Tuple[int, str, int]] = []
    for name, centroid in centroids.items():
        related = corridor_events.get(name, [])
        congestion = compute_corridor_congestion(name, hour, weekday, month, related)
        priority = 1 if name in active_names else 0
        scored.append((priority, congestion, name))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected = [name for _, _, name in scored[:max_corridors]]

    corridors: List[dict] = []
    for idx, name in enumerate(selected, start=1):
        centroid = centroids[name]
        related = corridor_events.get(name, [])
        congestion = compute_corridor_congestion(name, hour, weekday, month, related)
        path = build_corridor_path(name, centroid, related)
        corridors.append({
            'id': f'c{idx}',
            'name': name,
            'congestion': congestion,
            'status': _risk_status(congestion),
            'path': path,
            'active_events': len(related),
        })

    return corridors


def build_congestion_trend(
    hour: int,
    weekday: int,
    month: int,
    events: List[dict],
    *,
    window_hours: int = 12,
    start_hour: int = 6,
) -> List[dict]:
    """Hourly average corridor congestion forecast for chart series."""
    centroids = get_centroid_map()
    corridor_names = list(centroids.keys())[:8] or ['CBD 2']

    series: List[dict] = []
    for i in range(window_hours):
        h = (start_hour + i) % 24
        values = []
        for name in corridor_names:
            related = [ev for ev in events if map_event_to_corridor(ev) == name]
            values.append(compute_corridor_congestion(name, h, weekday, month, related))
        avg = int(round(sum(values) / max(len(values), 1)))
        series.append({'t': f'{h:02d}:00', 'value': avg})
    return series
