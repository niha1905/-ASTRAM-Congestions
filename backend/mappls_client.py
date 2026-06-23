"""
Shared Mappls (MapmyIndia) API helpers for routing and polyline decoding.

Uses the current route.mappls.com endpoint with access_token auth (Aug 2025+),
with OAuth client-credentials fallback and legacy advancedmaps URL when needed.
"""
import logging
import os
import time
from typing import List, Optional, Tuple

import requests as http_requests

logger = logging.getLogger(__name__)

MAPPLS_REST_API_KEY = os.environ.get('MAPPLS_REST_API_KEY', '')
MAPPLS_WEB_SDK_KEY = os.environ.get('MAPPLS_WEB_SDK_KEY', '') or MAPPLS_REST_API_KEY
MAPPLS_CLIENT_ID = os.environ.get('MAPPLS_CLIENT_ID', '')
MAPPLS_CLIENT_SECRET = os.environ.get('MAPPLS_CLIENT_SECRET', '')
MAPPLS_OAUTH_URL = os.environ.get(
    'MAPPLS_OAUTH_URL',
    'https://outpost.mappls.com/api/security/oauth/token',
)

_route_cache: dict = {}
_alt_route_cache: dict = {}
_route_fail_cache: dict = {}
_ROUTE_FAIL_TTL_SEC = 300
_consecutive_route_failures = 0
_ROUTE_FAILURE_THRESHOLD = 2
_oauth_cache: dict = {'access_token': None, 'expires_at': 0.0}


def is_mappls_configured() -> bool:
    return bool(MAPPLS_REST_API_KEY or (MAPPLS_CLIENT_ID and MAPPLS_CLIENT_SECRET))


def _fetch_oauth_token(force_refresh: bool = False) -> Optional[str]:
    if not MAPPLS_CLIENT_ID or not MAPPLS_CLIENT_SECRET:
        return None

    now = time.time()
    cached = _oauth_cache.get('access_token')
    expires_at = float(_oauth_cache.get('expires_at') or 0)
    if cached and not force_refresh and now < expires_at:
        return cached

    try:
        resp = http_requests.post(
            MAPPLS_OAUTH_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': MAPPLS_CLIENT_ID,
                'client_secret': MAPPLS_CLIENT_SECRET,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10,
        )
        logger.debug('[mappls] OAuth response status=%s body=%s', resp.status_code, resp.text[:1000])
        resp.raise_for_status()
        data = resp.json()
        token = data.get('access_token')
        if not token:
            logger.warning('[mappls] OAuth response missing access_token')
            return None

        expires_in = int(data.get('expires_in') or 3600)
        _oauth_cache['access_token'] = token
        _oauth_cache['expires_at'] = now + max(expires_in - 60, 60)
        logger.info('[mappls] OAuth access token refreshed (expires_in=%ss)', expires_in)
        return token
    except Exception as exc:
        logger.warning('[mappls] OAuth token fetch failed: %s', exc)
        return None


def get_mappls_access_token(force_refresh: bool = False) -> Optional[str]:
    """Return a Mappls access token for routing.

    Prefer the `MAPPLS_REST_API_KEY` (SDK/REST key) when available because some
    Mappls projects issue OAuth tokens that are not accepted by the Directions
    API. Fall back to OAuth client-credentials when REST key is absent.
    """
    # Diagnostic: avoid printing credential values; use logging at debug level instead.

    # Prefer REST/SDK key for routing calls if configured.
    if MAPPLS_REST_API_KEY:
        return MAPPLS_REST_API_KEY

    # Otherwise attempt OAuth client-credentials.
    if MAPPLS_CLIENT_ID and MAPPLS_CLIENT_SECRET:
        token = _fetch_oauth_token(force_refresh=force_refresh)
        if token:
            return token

    return None


def decode_polyline(encoded: str, precision: int = 5) -> List[List[float]]:
    """Decode an OSRM / Google encoded polyline into [[lat, lon], ...] pairs."""
    factor = 10 ** precision
    coords: List[List[float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
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


def to_mappls_coord(latlon_str: str) -> str:
    """Convert 'lat,lon' to Mappls 'lon,lat' coordinate string."""
    parts = latlon_str.strip().split(',')
    lat = parts[0].strip()
    lon = parts[1].strip()
    return f'{lon},{lat}'


def _build_coord_str(origin: str, destination: str, waypoints: Optional[str] = None) -> str:
    coord_parts = [to_mappls_coord(origin)]
    if waypoints:
        for wp in waypoints.split('|'):
            if wp.strip():
                coord_parts.append(to_mappls_coord(wp.strip()))
    coord_parts.append(to_mappls_coord(destination))
    return ';'.join(coord_parts)


def _route_request_cache_key(coord_str: str, alternatives: bool) -> str:
    return f'{coord_str}|{alternatives}'


def _is_route_fail_cached(cache_key: str) -> bool:
    failed_at = _route_fail_cache.get(cache_key)
    if failed_at is None:
        return False
    if time.time() - failed_at >= _ROUTE_FAIL_TTL_SEC:
        _route_fail_cache.pop(cache_key, None)
        return False
    return True


def _cache_route_failure(cache_key: str) -> None:
    _route_fail_cache[cache_key] = time.time()


def _request_routes(
    coord_str: str,
    api_key: Optional[str] = None,
    alternatives: bool = False,
) -> Optional[dict]:
    global _consecutive_route_failures
    if _consecutive_route_failures >= _ROUTE_FAILURE_THRESHOLD:
        return None

    cache_key = _route_request_cache_key(coord_str, alternatives)
    if _is_route_fail_cached(cache_key):
        return None

    key = api_key or MAPPLS_REST_API_KEY
    if not key:
        return None

    params = {
        'overview': 'full',
        'geometries': 'polyline',
    }
    if alternatives:
        params['alternatives'] = 'true'

    legacy_url = f'https://apis.mappls.com/advancedmaps/v1/{key}/route_adv/driving/{coord_str}'
    try:
        resp = http_requests.get(legacy_url, params=params, timeout=4)
        # Log request/response at debug level instead of printing to stdout.
        try:
            logger.debug('LEGACY ROUTE URL: %s', resp.url)
            logger.debug('STATUS: %s', resp.status_code)
            logger.debug('BODY: %s', resp.text[:2000])
        except Exception:
            logger.debug('[mappls] Failed to log legacy route response details', exc_info=True)

        logger.debug('[mappls] Legacy route request url=%s status=%s body=%s', legacy_url, resp.status_code, resp.text[:1000])
        data = resp.json()
        if data.get('code') in ('Ok', 'OK') and data.get('routes'):
            _consecutive_route_failures = 0
            return data

        primary_code = data.get('code', 'UNKNOWN')
        logger.warning('[mappls] Legacy Route API code=%s for coords=%s', primary_code, coord_str[:80])
        _cache_route_failure(cache_key)
        _consecutive_route_failures += 1
        return None
    except Exception as exc:
        logger.warning('[mappls] Legacy Route fetch exception: %s', exc)
        _cache_route_failure(cache_key)
        _consecutive_route_failures += 1
        return None


def fetch_mappls_route(
    origin: str,
    destination: str,
    waypoints: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[List[List[float]]]:
    """
    Fetch a single driving route and return [[lat, lon], ...] or None on failure.

    Args:
        origin: 'lat,lon' start point.
        destination: 'lat,lon' end point.
        waypoints: Pipe-separated 'lat,lon|lat,lon' via points.
        api_key: Optional override for MAPPLS_REST_API_KEY.
    """
    cache_key = f'mappls|{origin}|{destination}|{waypoints or ""}'
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    coord_str = _build_coord_str(origin, destination, waypoints)
    data = _request_routes(coord_str, api_key=api_key, alternatives=False)
    if not data:
        return None

    encoded = data['routes'][0].get('geometry')
    if not encoded:
        return None

    decoded = decode_polyline(encoded)
    if len(decoded) < 2:
        logger.warning('[mappls] Decoded route has fewer than 2 points for %s -> %s', origin, destination)
        return None

    _route_cache[cache_key] = decoded
    logger.info('[mappls] Fetched %d-point route %s -> %s', len(decoded), origin, destination)
    return decoded


def fetch_mappls_routes_with_alternatives(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    api_key: Optional[str] = None,
) -> Tuple[Optional[List[List[float]]], Optional[List[List[float]]], Optional[float], Optional[float], Optional[int], Optional[int]]:
    """
    Fetch primary and alternate routes between two lat/lon pairs.

    Returns:
        (primary_path, alt_path, dist_primary_km, dist_alt_km, eta_primary_min, eta_alt_min)
    """
    origin = f'{origin_lat},{origin_lon}'
    destination = f'{dest_lat},{dest_lon}'
    alt_cache_key = f'mappls_alt|{origin}|{destination}'
    if alt_cache_key in _alt_route_cache:
        return _alt_route_cache[alt_cache_key]

    coord_str = _build_coord_str(origin, destination)
    data = _request_routes(coord_str, api_key=api_key, alternatives=True)
    if not data:
        result = (None, None, None, None, None, None)
        _alt_route_cache[alt_cache_key] = result
        return result

    routes = data['routes']
    primary = routes[0]
    primary_path = decode_polyline(primary.get('geometry', '')) if primary.get('geometry') else None
    if not primary_path or len(primary_path) < 2:
        result = (None, None, None, None, None, None)
        _alt_route_cache[alt_cache_key] = result
        return result

    dist_primary = primary.get('distance', 0) / 1000.0 if primary.get('distance') is not None else None
    eta_primary = round(primary.get('duration', 0) / 60.0) if primary.get('duration') is not None else None

    alt_path = None
    dist_alt = None
    eta_alt = None
    if len(routes) > 1:
        alt = routes[1]
        if alt.get('geometry'):
            alt_path = decode_polyline(alt['geometry'])
        if alt.get('distance') is not None:
            dist_alt = alt.get('distance', 0) / 1000.0
        if alt.get('duration') is not None:
            eta_alt = round(alt.get('duration', 0) / 60.0)

    result = (primary_path, alt_path, dist_primary, dist_alt, eta_primary, eta_alt)
    _alt_route_cache[alt_cache_key] = result
    return result
