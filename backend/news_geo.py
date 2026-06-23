"""
Resolve news headlines to map coordinates and Mappls driving routes.

Geocoding priority:
  1. Longest keyword match in BANGALORE_LOCATIONS (title + summary)
  2. Scraper-extracted location field → Mappls Atlas geocode
  3. Full headline → Mappls Atlas geocode
  4. Bangalore city-centre fallback

Routing uses Mappls route_adv with alternatives=true (OAuth / REST key via mappls_client).
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import requests

from .config import BANGALORE_LOCATIONS
from .mappls_client import (
    fetch_mappls_route,
    fetch_mappls_routes_with_alternatives,
    get_mappls_access_token,
    is_mappls_configured,
)

logger = logging.getLogger(__name__)

BANGALORE_CENTER = (12.9716, 77.5946)

# Curated corridor endpoints for well-known localities (lat,lon strings).
LOCATION_ROUTE_SPECS = {
    'koramangala': {
        'affected': 'Hosur Road (Koramangala Section)',
        'divert_to': 'Sarjapur Road / Inner Ring Road Bypass',
        'origin': 'Koramangala 4th Block',
        'destination': 'Koramangala 6th Block',
        'diversion_waypoints': 'Sarjapur Road|Inner Ring Road|Koramangala Bypass',
    },
    'indiranagar': {
        'affected': '100 Feet Road (Indiranagar Corridor)',
        'divert_to': 'Old Airport Road & CMH Road Bypass',
        'origin': 'Indiranagar 100 Feet Road',
        'destination': 'Indiranagar 1st Stage',
        'diversion_waypoints': 'Old Airport Road|CMH Road|Domlur',
    },
    'mg road': {
        'affected': 'MG Road (CBD Hub)',
        'divert_to': 'Richmond Road / Residency Road Detour',
        'origin': 'MG Road, Bengaluru',
        'destination': 'Residency Road, Bengaluru',
        'diversion_waypoints': 'Richmond Road|Brigade Road',
    },
    'whitefield': {
        'affected': 'Whitefield Main Road (IT Corridor)',
        'divert_to': 'ITPL Main Road & Varthur Road Bypass',
        'origin': 'Whitefield Main Road',
        'destination': 'ITPL Main Road',
        'diversion_waypoints': 'Varthur Road|Whitefield Satellite Town|ITPL',
    },
    'electronic city': {
        'affected': 'Hosur Road Tollway (Electronic City)',
        'divert_to': 'Neeladri Road & West Phase Bypass',
        'origin': 'Electronic City',
        'destination': 'Electronic City Phase 1',
        'diversion_waypoints': 'Hosur Road|Neeladri Road|Electronic City Gate',
    },
    'yelahanka': {
        'affected': 'Doddaballapur Road (Yelahanka Sector)',
        'divert_to': 'Major Sandeep Unnikrishnan Road Detour',
        'origin': 'Yelahanka',
        'destination': 'Yelahanka New Town',
        'diversion_waypoints': 'Doddaballapur Road|Yelahanka Satellite Town',
    },
    'hebbal': {
        'affected': 'Hebbal Flyover Junction',
        'divert_to': 'Outer Ring Road (ORR) North Bypass',
        'origin': 'Hebbal Flyover',
        'destination': 'Hebbal',
        'diversion_waypoints': 'Outer Ring Road North|Bellary Road|Hebbal Ring Road',
    },
    'jayanagar': {
        'affected': 'Jayanagar 4th Block Main Road',
        'divert_to': 'Rashtreeya Vidyalaya Road Bypass',
        'origin': 'Jayanagar 4th Block',
        'destination': 'Jayanagar 3rd Block',
        'diversion_waypoints': 'Rashtreeya Vidyalaya Road|Banashankari',
    },
    'rajajinagar': {
        'affected': 'Dr. Rajkumar Road (Rajajinagar Sector)',
        'divert_to': 'West of Chord Road Bypass Route',
        'origin': 'Dr Rajkumar Road',
        'destination': 'Rajajinagar',
        'diversion_waypoints': 'Chord Road|Malleswaram',
    },
}


def _in_bangalore(lat: float, lon: float) -> bool:
    return 12.73 <= lat <= 13.17 and 77.38 <= lon <= 77.88


def _parse_latlon(value: str) -> Tuple[float, float]:
    parts = value.strip().split(',')
    return float(parts[0].strip()), float(parts[1].strip())


def _normalize_route_key(matched_key: Optional[str]) -> Optional[str]:
    if not matched_key:
        return None
    if matched_key in LOCATION_ROUTE_SPECS:
        return matched_key
    for spec_key in LOCATION_ROUTE_SPECS:
        if spec_key in matched_key or matched_key in spec_key:
            return spec_key
    return matched_key


def _is_latlon_str(value: str) -> bool:
    parts = value.split(',')
    if len(parts) != 2:
        return False
    try:
        float(parts[0].strip())
        float(parts[1].strip())
        return True
    except Exception:
        return False


def _ensure_coord(value: str) -> Tuple[float, float]:
    """Return (lat, lon) for a value that may be a 'lat,lon' string or a place name.

    If the value is already numeric lat,lon, parse and return. Otherwise attempt
    Mappls geocoding; fall back to Bangalore center when geocoding fails.
    """
    if not value:
        return BANGALORE_CENTER

    v = value.strip()
    if _is_latlon_str(v):
        try:
            return _parse_latlon(v)
        except Exception:
            return BANGALORE_CENTER

    # Not a numeric lat/lon — attempt geocoding (adds Bangalore context)
    pos = geocode_with_mappls(v)
    if pos:
        return pos
    return BANGALORE_CENTER


def geocode_with_mappls(query: str) -> Optional[Tuple[float, float]]:
    """Geocode an address/place string using Mappls Atlas API."""
    token = get_mappls_access_token()
    if not token or not query.strip():
        return None

    try:
        resp = requests.get(
            'https://atlas.mappls.com/api/places/geocode',
            params={
                'address': f'{query.strip()} Bangalore Karnataka',
                'itemCount': 1,
                'access_token': token,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get('copResults', {}) or {}
        lat = results.get('latitude') or results.get('lat')
        lng = results.get('longitude') or results.get('lng')
        if lat is None or lng is None:
            return None

        lat_f, lon_f = float(lat), float(lng)
        if _in_bangalore(lat_f, lon_f):
            return lat_f, lon_f
    except Exception as exc:
        logger.debug('[news_geo] Mappls geocode failed for %r: %s', query[:80], exc)

    return None


def _keyword_match(text: str) -> Optional[str]:
    matches = [k for k in BANGALORE_LOCATIONS if k in text]
    if not matches:
        return None
    return max(matches, key=len)


def resolve_news_location(
    title: str,
    summary: str = '',
    scraper_location: Optional[str] = None,
) -> Tuple[float, float, str, Optional[str]]:
    """
    Resolve a news item to (lat, lon, zone_label, matched_location_key).

    Uses dictionary lookup first, then Mappls geocoding for extracted places/headlines.
    """
    tkn = f'{title} {summary or ""}'.lower()

    matched_key = _keyword_match(tkn)
    if matched_key:
        lat, lon = BANGALORE_LOCATIONS[matched_key]
        return lat, lon, matched_key.title(), matched_key

    if scraper_location:
        loc_key = _keyword_match(scraper_location.lower())
        if loc_key:
            lat, lon = BANGALORE_LOCATIONS[loc_key]
            return lat, lon, scraper_location, loc_key

        pos = geocode_with_mappls(scraper_location)
        if pos:
            return pos[0], pos[1], scraper_location, None

    headline_query = f'{title} Bangalore'.strip()[:240]
    pos = geocode_with_mappls(headline_query)
    if pos:
        zone = scraper_location or title[:48].strip() or 'Bangalore'
        return pos[0], pos[1], zone, None

    zone = scraper_location or 'Bangalore'
    return BANGALORE_CENTER[0], BANGALORE_CENTER[1], zone, None


def _offset_fallback_path(lat: float, lon: float) -> Tuple[list, list]:
    path = [
        [lat, lon],
        [lat - 0.008, lon + 0.006],
        [lat - 0.015, lon + 0.012],
        [lat - 0.022, lon + 0.018],
    ]
    diversion = [
        [lat, lon],
        [lat + 0.010, lon - 0.008],
        [lat + 0.015, lon + 0.005],
        [lat + 0.008, lon + 0.020],
        [lat - 0.005, lon + 0.025],
        [lat - 0.022, lon + 0.018],
    ]
    return path, diversion


def build_traffic_plan(
    matched_key: Optional[str],
    found_pos: Tuple[float, float],
    zone: str,
) -> dict:
    """
    Build affected + alternate route geometry using Mappls Route API.

    Primary route  = default/fastest road segment (shown as affected road).
    Diversion path = Mappls alternate route, or waypoint-routed detour.
    """
    lat, lon = found_pos
    diversion_wp = None
    route_key = _normalize_route_key(matched_key)

    if route_key and route_key in LOCATION_ROUTE_SPECS:
        spec = LOCATION_ROUTE_SPECS[route_key]
        o_lat, o_lon = _ensure_coord(spec.get('origin', ''))
        d_lat, d_lon = _ensure_coord(spec.get('destination', ''))
        affected = spec['affected']
        divert_to = spec['divert_to']
        diversion_wp = spec.get('diversion_waypoints')
        # Build origin/destination strings as 'lat,lon'
        origin_str = f'{o_lat},{o_lon}'
        dest_str = f'{d_lat},{d_lon}'

        # If diversion waypoints are present, ensure they are lat,lon pairs
        if diversion_wp:
            wp_parts = []
            for wp in diversion_wp.split('|'):
                wp = wp.strip()
                if not wp:
                    continue
                if _is_latlon_str(wp):
                    wp_parts.append(wp)
                else:
                    latlon = _ensure_coord(wp)
                    wp_parts.append(f'{latlon[0]},{latlon[1]}')
            diversion_wp = '|'.join(wp_parts) if wp_parts else None
    else:
        o_lat, o_lon = lat, lon
        d_lat = round(lat - 0.022, 6)
        d_lon = round(lon + 0.018, 6)
        affected = f'Main arterial road near {zone}'
        divert_to = f'Alternate corridor bypassing {zone}'
        origin_str = f'{o_lat},{o_lon}'
        dest_str = f'{d_lat},{d_lon}'

    path = None
    alt_path = None
    dist_primary = dist_alt = eta_primary = eta_alt = None
    primary_from_mappls = False
    alt_from_mappls = False

    if is_mappls_configured():
        path, alt_path, dist_primary, dist_alt, eta_primary, eta_alt = fetch_mappls_routes_with_alternatives(
            o_lat, o_lon, d_lat, d_lon,
        )
        if path:
            primary_from_mappls = True
        if alt_path:
            alt_from_mappls = True

        if path and not alt_path and diversion_wp:
            alt_path = fetch_mappls_route(origin_str, dest_str, waypoints=diversion_wp)
            if alt_path:
                alt_from_mappls = True

    fb_path, fb_div = _offset_fallback_path(lat, lon)
    if path is None:
        path = fb_path
    if alt_path is None:
        alt_path = fb_div

    if primary_from_mappls and alt_from_mappls:
        source = 'mappls'
    elif primary_from_mappls or alt_from_mappls:
        source = 'mappls_partial'
    else:
        source = 'offset_fallback'

    plan = {
        'affected': affected,
        'divert_to': divert_to,
        'path': path,
        'diversion_path': alt_path,
        'source': source,
        'origin': [o_lat, o_lon],
        'destination': [d_lat, d_lon],
    }
    if dist_primary is not None:
        plan['distance_km'] = round(dist_primary, 2)
    if dist_alt is not None:
        plan['alt_distance_km'] = round(dist_alt, 2)
    if eta_primary is not None:
        plan['eta_min'] = eta_primary
    if eta_alt is not None:
        plan['alt_eta_min'] = eta_alt

    return plan
