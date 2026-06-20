"""
News -> Events endpoint
Scrapes recent news items and runs lightweight inference through existing predictors.
Routes use the Mappls (MapmyIndia) Route API for real road-following polylines when
MAPPLS_REST_API_KEY is configured; falls back to offset-based paths otherwise.
"""
import os
import logging
import requests as http_requests
from flask import Blueprint, jsonify, request
from ..scrapers.news_scraper import fetch_google_news_rss
from ..models.predictors import ClosurePredictor, ImpactScorePredictor, ResourceDeploymentPredictor, HotspotRiskPredictor
from ..config import BANGALORE_LOCATIONS, NEWS_MAX_ITEMS
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


# Minimal sentiment helpers (best-effort, offline)
POSITIVE_WORDS = set(['clear', 'reopen', 'relief', 'rescued', 'safe', 'resolved', 'managed', 'minor', 'help'])
NEGATIVE_WORDS = set(['injury', 'fatal', 'dead', 'damage', 'accident', 'collision', 'riot', 'protest', 'fire', 'stampede', 'closure', 'blocked'])

# BANGALORE_LOCATIONS imported from config.py (single source of truth)

# Route specifications used to fetch Google Maps Directions for each known location.
# 'origin' / 'destination' are "lat,lon" strings.
# 'diversion_waypoints' is a pipe-separated "lat,lon|lat,lon" string passed to the
# Directions API 'waypoints' parameter to route via alternate roads.
LOCATION_ROUTE_SPECS = {
    'koramangala': {
        'affected': 'Hosur Road (Koramangala Section)',
        'divert_to': 'Sarjapur Road / Inner Ring Road Bypass',
        'origin': '12.9352,77.6245',
        'destination': '12.9150,77.6350',
        'diversion_waypoints': '12.9420,77.6200|12.9480,77.6320|12.9350,77.6480',
    },
    'indiranagar': {
        'affected': '100 Feet Road (Indiranagar Corridor)',
        'divert_to': 'Old Airport Road & CMH Road Bypass',
        'origin': '12.9719,77.6412',
        'destination': '12.9520,77.6420',
        'diversion_waypoints': '12.9740,77.6530|12.9640,77.6580|12.9560,77.6490',
    },
    'mg road': {
        'affected': 'MG Road (CBD Hub)',
        'divert_to': 'Richmond Road / Residency Road Detour',
        'origin': '12.9754,77.6050',
        'destination': '12.9760,77.5870',
        'diversion_waypoints': '12.9690,77.6070|12.9660,77.5960',
    },
    'whitefield': {
        'affected': 'Whitefield Main Road (IT Corridor)',
        'divert_to': 'ITPL Main Road & Varthur Road Bypass',
        'origin': '12.9699,77.7490',
        'destination': '12.9830,77.7560',
        'diversion_waypoints': '12.9640,77.7430|12.9590,77.7550|12.9720,77.7620',
    },
    'electronic city': {
        'affected': 'Hosur Road Tollway (Electronic City)',
        'divert_to': 'Neeladri Road & West Phase Bypass',
        'origin': '12.8498,77.6624',
        'destination': '12.8320,77.6780',
        'diversion_waypoints': '12.8560,77.6580|12.8510,77.6470|12.8390,77.6560',
    },
    'yelahanka': {
        'affected': 'Doddaballapur Road (Yelahanka Sector)',
        'divert_to': 'Major Sandeep Unnikrishnan Road Detour',
        'origin': '13.0845,77.5938',
        'destination': '13.0960,77.5990',
        'diversion_waypoints': '13.0810,77.5840|13.0970,77.5870',
    },
    'hebbal': {
        'affected': 'Hebbal Flyover Junction',
        'divert_to': 'Outer Ring Road (ORR) North Bypass',
        'origin': '13.0358,77.5966',
        'destination': '13.0180,77.5940',
        'diversion_waypoints': '13.0420,77.6080|13.0290,77.6120|13.0190,77.6010',
    },
    'jayanagar': {
        'affected': 'Jayanagar 4th Block Main Road',
        'divert_to': 'Rashtreeya Vidyalaya Road Bypass',
        'origin': '12.9372,77.5956',
        'destination': '12.9230,77.5950',
        'diversion_waypoints': '12.9390,77.5840|12.9300,77.5820',
    },
    'rajajinagar': {
        'affected': 'Dr. Rajkumar Road (Rajajinagar Sector)',
        'divert_to': 'West of Chord Road Bypass Route',
        'origin': '12.9979,77.5546',
        'destination': '12.9830,77.5510',
        'diversion_waypoints': '12.9990,77.5430|12.9910,77.5410',
    },
}

# ─── Mappls (MapmyIndia) Route API helpers ────────────────────────────────────

_MAPPLS_API_KEY = os.environ.get('MAPPLS_REST_API_KEY', '')

# In-process cache: cache_key -> [[lat, lon], ...]
_route_cache = {}


def _decode_polyline(encoded, precision=5):
    """
    Decode an OSRM / Google encoded polyline string into [[lat, lon], ...] pairs.
    Works with both standard precision-5 (Google / Mappls default) and
    precision-6 polylines; pass precision=6 for polyline6 responses.
    """
    factor = 10 ** precision
    coords = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        # Decode latitude delta
        result = 0
        shift = 0
        while True:
            if index >= length:
                break
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        # Decode longitude delta
        result = 0
        shift = 0
        while True:
            if index >= length:
                break
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coords.append([round(lat / factor, precision + 1), round(lng / factor, precision + 1)])

    return coords


def _to_mappls_coord(latlon_str):
    """
    Convert a 'lat,lon' string (as stored in LOCATION_ROUTE_SPECS) to
    Mappls coordinate format 'lon,lat' required by the route_adv API.
    """
    parts = latlon_str.strip().split(',')
    lat = parts[0].strip()
    lon = parts[1].strip()
    return f'{lon},{lat}'


def fetch_mappls_route(origin, destination, waypoints=None, api_key=None):
    """
    Call the Mappls route_adv API and return a decoded polyline as
    [[lat, lon], ...], or None if the call fails or the key is missing.

    Mappls uses OSRM-compatible routing: coordinates are embedded in the URL
    path in 'lon,lat' order, separated by semicolons. Waypoints are inserted
    between origin and destination in the same coordinate string.

    Results are cached in-process to avoid redundant API calls.

    Args:
        origin:      'lat,lon' string for the route start.
        destination: 'lat,lon' string for the route end.
        waypoints:   Pipe-separated 'lat,lon|lat,lon' string for via-points.
        api_key:     Mappls REST API key; falls back to module-level key.
    """
    key = api_key or _MAPPLS_API_KEY
    cache_key = f'mappls|{origin}|{destination}|{waypoints or ""}'

    if cache_key in _route_cache:
        return _route_cache[cache_key]

    if not key:
        logger.warning('[mappls] MAPPLS_REST_API_KEY not set; using fallback offset route.')
        return None

    # Build semicolon-separated 'lon,lat' coordinate string for Mappls
    coord_parts = [_to_mappls_coord(origin)]
    if waypoints:
        for wp in waypoints.split('|'):
            if wp.strip():
                coord_parts.append(_to_mappls_coord(wp.strip()))
    coord_parts.append(_to_mappls_coord(destination))
    coord_str = ';'.join(coord_parts)

    url = f'https://apis.mappls.com/advancedmaps/v1/{key}/route_adv/driving/{coord_str}'

    try:
        resp = http_requests.get(
            url,
            params={'overview': 'full', 'geometries': 'polyline'},
            timeout=6,
        )
        data = resp.json()
        code = data.get('code', 'UNKNOWN')

        if code != 'Ok':
            logger.warning('[mappls] Route API code=%s for %s -> %s', code, origin, destination)
            return None

        encoded = data['routes'][0]['geometry']
        decoded = _decode_polyline(encoded)

        if len(decoded) < 2:
            logger.warning('[mappls] Decoded route has fewer than 2 points for %s -> %s', origin, destination)
            return None

        _route_cache[cache_key] = decoded
        logger.info('[mappls] Fetched %d-point route %s -> %s', len(decoded), origin, destination)
        return decoded

    except Exception as exc:
        logger.warning('[mappls] Route fetch exception: %s', exc)
        return None


def _offset_fallback_path(lat, lon):
    """
    Generate a simple offset-based affected path and diversion path around (lat, lon).
    Used when the Mappls API is unavailable or returns an error.
    Returns (path, diversion_path) as [[lat, lon], ...] lists.
    """
    path = [
        [lat,          lon         ],
        [lat - 0.008,  lon + 0.006 ],
        [lat - 0.015,  lon + 0.012 ],
        [lat - 0.022,  lon + 0.018 ],
    ]
    diversion = [
        [lat,          lon         ],
        [lat + 0.010,  lon - 0.008 ],
        [lat + 0.015,  lon + 0.005 ],
        [lat + 0.008,  lon + 0.020 ],
        [lat - 0.005,  lon + 0.025 ],
        [lat - 0.022,  lon + 0.018 ],
    ]
    return path, diversion


def _build_traffic_plan(matched_key, found_pos, zone):
    """
    Build a traffic_plan dict with `path` and `diversion_path` populated by the
    Mappls Route API. Falls back to offset-based geometry on API failure.
    """
    if matched_key and matched_key in LOCATION_ROUTE_SPECS:
        spec = LOCATION_ROUTE_SPECS[matched_key]
        origin = spec['origin']
        destination = spec['destination']
        diversion_wp = spec.get('diversion_waypoints')

        # Fetch the main (affected) road route via Mappls
        path = fetch_mappls_route(origin, destination)

        # Fetch the diversion route (same origin/dest but routed via waypoints)
        diversion = fetch_mappls_route(origin, destination, waypoints=diversion_wp)

        # Graceful fallback per leg
        if path is None or diversion is None:
            fb_lat, fb_lon = BANGALORE_LOCATIONS[matched_key]
            fb_path, fb_div = _offset_fallback_path(fb_lat, fb_lon)
            path = path if path is not None else fb_path
            diversion = diversion if diversion is not None else fb_div

        return {
            'affected': spec['affected'],
            'divert_to': spec['divert_to'],
            'path': path,
            'diversion_path': diversion,
            'source': 'mappls',
        }

    else:
        # Unknown / generic location: derive origin/destination from geocoded position
        lat, lon = found_pos
        origin = f'{lat},{lon}'
        destination = f'{round(lat - 0.022, 6)},{round(lon + 0.018, 6)}'
        diversion_wp = (
            f'{round(lat + 0.010, 6)},{round(lon - 0.008, 6)}|'
            f'{round(lat + 0.015, 6)},{round(lon + 0.005, 6)}|'
            f'{round(lat + 0.008, 6)},{round(lon + 0.020, 6)}'
        )

        path = fetch_mappls_route(origin, destination)
        diversion = fetch_mappls_route(origin, destination, waypoints=diversion_wp)

        fb_path, fb_div = _offset_fallback_path(lat, lon)

        return {
            'affected': f'Main Arterial Road near {zone}',
            'divert_to': f'{zone} Ring Road / Peripheral Bypass',
            'path': path if path is not None else fb_path,
            'diversion_path': diversion if diversion is not None else fb_div,
            'source': 'mappls' if (path is not None) else 'offset_fallback',
        }


# ─── Blueprint ────────────────────────────────────────────────────────────────

news_bp = Blueprint('news', __name__, url_prefix='/api/news')


def infer_event_type(title):
    t = title.lower()
    # planned events
    if any(k in t for k in ['concert', 'match', 'festival', 'celebration', 'marathon', 'parade', 'conference', 'exhibition', 'fair', 'ceremony', 'procession', 'march', 'event', 'program', 'function', 'gathering', 'meeting', 'sports', 'tournament', 'vip', 'motorcade', 'state visit', 'scheduled', 'announced']):
        return 'planned'
    # unplanned incidents
    if any(k in t for k in ['protest', 'fire', 'accident', 'collision', 'stampede', 'riot', 'evacuation', 'collapse', 'sinkhole', 'flood']):
        return 'unplanned'
    return 'unplanned'


def parse_published(published):
    """Parse a published timestamp that may be RFC 822 (Google News RSS)
    or ISO-8601, falling back to current UTC time if unparseable."""
    if not published:
        return datetime.utcnow()
    # Try ISO 8601 first
    try:
        return datetime.fromisoformat(published)
    except ValueError:
        pass
    # Fall back to RFC 822 (standard RSS pubDate format)
    try:
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.utcnow()


@news_bp.route('/events', methods=['GET'])
def news_events():
    """Returns recent news items and ML-driven impact estimates.

    Optional query params:
      q: search query (default: 'bangalore event traffic')
      limit: max items
    """
    q = request.args.get('q', 'bangalore event traffic')
    limit = int(request.args.get('limit', NEWS_MAX_ITEMS))

    items = fetch_google_news_rss(q, max_items=limit)
    results = []

    for it in items:
        title = it.get('title', '')
        published = it.get('published')
        dt = parse_published(published)

        hour = dt.hour
        weekday = dt.weekday()

        event_type = infer_event_type(title)
        priority = 'High' if 'mass' in title.lower() or 'large' in title.lower() else 'Medium'

        # sentiment (simple lexicon-based)
        tkn = title.lower() + ' ' + (it.get('summary') or '')
        pos = sum(1 for w in POSITIVE_WORDS if w in tkn)
        neg = sum(1 for w in NEGATIVE_WORDS if w in tkn)
        if pos > neg:
            sentiment = 'positive'
        elif neg > pos:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        # best-effort geocode from title/summary using our small mapping
        found_pos = None
        matched_key = None
        for k, coords in BANGALORE_LOCATIONS.items():
            if k in tkn:
                found_pos = coords
                zone = k.title()
                matched_key = k
                break
        if not found_pos:
            # default center of Bangalore
            found_pos = (12.9716, 77.5946)
            zone = 'Bangalore'

        # Build traffic plan using Google Maps Directions API
        traffic_plan = _build_traffic_plan(matched_key, found_pos, zone)

        corridor = traffic_plan.get('affected', 'Unknown')

        # Extract source name from title (e.g. "Title - Source" or "Title | Source")
        news_source = 'Google News'
        title_clean = title
        if ' - ' in title:
            parts = title.rsplit(' - ', 1)
            title_clean = parts[0]
            news_source = parts[1]
        elif ' | ' in title:
            parts = title.rsplit(' | ', 1)
            title_clean = parts[0]
            news_source = parts[1]

        news_data = {
            'title': title_clean,
            'original_title': title,
            'link': it.get('link', ''),
            'summary': it.get('summary', ''),
            'published': it.get('published'),
            'source': news_source,
        }

        # closure prediction — uses the geocoded zone/corridor
        closure = ClosurePredictor.predict(event_type=event_type, zone=zone, corridor=corridor, priority=priority, hour=hour, duration_min=30)
        closure_prob = closure.get('closure_probability', 0) if isinstance(closure, dict) else 0

        # impact score
        impact = ImpactScorePredictor.predict(event_cause=event_type, corridor=corridor, priority=priority, hour=hour, weekday=weekday, closure_probability=closure_prob)

        # resource recommendation
        resources = ResourceDeploymentPredictor.predict(event_type=event_type, priority=priority, zone=zone, corridor=corridor, hour=hour, closure_prob=closure_prob)

        # generate simple pre-measures / recommendations text
        recs = []
        if closure_prob >= 50:
            recs.append('Prepare road closure signage and barricades')
        if resources.get('officers_needed', 0) >= 4:
            recs.append('Deploy additional traffic officers to nearby junctions')
        if impact.get('impact_score', 0) >= 60:
            recs.append('Advise public transport diversions and issue traveler alerts')
        if sentiment == 'negative':
            recs.append('Monitor crowd and emergency services readiness')

        results.append({
            'news': news_data,
            'inferred': {
                'event_type': event_type,
                'priority': priority,
                'hour': hour,
                'weekday': weekday,
                'zone': zone,
            },
            'predictions': {
                'closure': closure,
                'impact': impact,
                'resources': resources,
            },
            'sentiment': sentiment,
            'position': {'lat': found_pos[0], 'lon': found_pos[1]},
            'pre_measures': recs,
            'traffic_plan': traffic_plan,
        })

    return jsonify({'count': len(results), 'items': results}), 200