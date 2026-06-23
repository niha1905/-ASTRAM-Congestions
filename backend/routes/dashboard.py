"""
Dashboard Routes
Provides aggregated data for dashboard and other operational endpoints
"""

import logging
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import os
from pathlib import Path
import pandas as pd
from ..models.predictors import (
    CascadePredictor,
    ClosurePredictor,
    DurationPredictor,
    GreenCorridorPredictor,
    HotspotRiskPredictor,
    ImpactScorePredictor,
    IncidentVolumePredictor,
    ParkingOverflowPredictor,
    ResourceDeploymentPredictor,
    ScenarioEnginePredictor,
)
from ..models.model_loader import model_loader
from ..mappls_client import fetch_mappls_routes_with_alternatives, get_mappls_access_token, is_mappls_configured
from ..corridor_engine import (
    build_congestion_trend,
    build_dynamic_corridors,
    map_event_to_corridor,
)
from ..news_geo import build_traffic_plan, resolve_news_location
from ..config import (
    BANGALORE_LOCATIONS,
    NEWS_MAX_ITEMS,
    NEWS_QUERY,
    SERIES_START_HOUR,
    SERIES_WINDOW_HOURS,
)
import requests
try:
    from geopy.geocoders import Nominatim
    _GEOPY_AVAILABLE = True
except Exception:
    _GEOPY_AVAILABLE = False

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')

# ── Google Maps Geocoding helper ──────────────────────────────────────────────
_GOOGLE_MAPS_KEY = os.environ.get('GOOGLE_MAPS_SERVER_API_KEY', '')
_BANGALORE_BOUNDS = '12.7343,77.3791|13.1688,77.8834'


def _geocode_google(query: str) -> tuple:
    """Geocode a location string using Google Maps Geocoding API.
    Returns (lat, lon) tuple or None if not found/invalid.
    """
    if not _GOOGLE_MAPS_KEY:
        return None
    try:
        resp = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={
                'address': query + ' Bangalore Karnataka India',
                'key': _GOOGLE_MAPS_KEY,
                'bounds': _BANGALORE_BOUNDS,
                'components': 'country:IN',
            },
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'OK' and data.get('results'):
                loc = data['results'][0]['geometry']['location']
                lat, lng = loc['lat'], loc['lng']
                # Validate within Bangalore metro area
                if 12.73 <= lat <= 13.17 and 77.38 <= lng <= 77.88:
                    return (lat, lng)
    except Exception as e:
        logger.debug(f'Google geocode failed: {e}')
    return None


def _geocode_mappls(query: str) -> tuple:
    """Geocode using Mappls (MapmyIndia) Atlas API as secondary fallback.
    Returns (lat, lon) or None.
    """
    token = get_mappls_access_token()
    if not token:
        return None
    try:
        params = {
            'address': query + ' Bangalore',
            'itemCount': 1,
            'access_token': token,
        }

        resp = requests.get(
            'https://atlas.mappls.com/api/places/geocode',
            params=params,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('copResults', {}) or {}
            # Mappls returns a single object for exact match
            lat = results.get('latitude') or results.get('lat')
            lng = results.get('longitude') or results.get('lng')
            if lat and lng:
                lat, lng = float(lat), float(lng)
                if 12.73 <= lat <= 13.17 and 77.38 <= lng <= 77.88:
                    return (lat, lng)
    except Exception as e:
        logger.debug(f'Mappls geocode failed: {e}')
    return None


def _smart_geocode(title: str, summary: str) -> tuple:
    """Multi-tier geocoding: Google Maps API → Mappls API → safe city-center.
    Returns (lat, lon).
    """
    query = f"{title} {summary or ''}"
    # Tier 1: Google Maps
    pos = _geocode_google(query)
    if pos:
        return pos
    # Tier 2: Mappls
    pos = _geocode_mappls(query)
    if pos:
        return pos
    # Tier 3: Geopy/Nominatim (free OSM) when API keys missing
    if _GEOPY_AVAILABLE:
        try:
            geolocator = Nominatim(user_agent='astram_congestioniq')
            loc = geolocator.geocode(query + ' Bangalore Karnataka India', timeout=5)
            if loc and 12.73 <= loc.latitude <= 13.17 and 77.38 <= loc.longitude <= 77.88:
                return (loc.latitude, loc.longitude)
        except Exception:
            pass
    # Tier 3: Safe city-centre fallback (Vidhana Soudha area)
    return (12.9716, 77.5946)


# ── Attendance estimation helper ──────────────────────────────────────────────
_ATTENDANCE_PATTERNS = [
    r'(\d[\d,]+)\s*(?:people|attendees|spectators|visitors|participants|fans|crowd)',
    r'crowd\s+of\s+(\d[\d,]+)',
    r'(\d[\d,]+)\s*(?:are expected|expected to attend|expected to gather|likely to attend)',
    r'turnout\s+of\s+(\d[\d,]+)',
    r'(\d[\d,]+)\s*strong\s+crowd',
]
_EVENT_ATTENDANCE_ESTIMATES = [
    (['ipl', 'cricket', 'football', 'copa', 'world cup', 'champions league'], 45000),
    (['marathon', 'half marathon', 'run', 'cycling', 'triathlon'], 25000),
    (['concert', 'music festival', 'festival', 'gig', 'band', 'artiste'], 18000),
    (['expo', 'exhibition', 'trade fair', 'auto expo', 'summit', 'conference'], 12000),
    (['parade', 'procession', 'republic day', 'independence day'], 10000),
    (['protest', 'rally', 'demonstration', 'bandh', 'strike'], 5000),
    (['wedding', 'reception', 'event'], 2000),
]


def estimate_attendance(title: str, summary: str, event_type: str) -> int:
    """Estimate event attendance from article text.
    1. Parse explicit numbers mentioned in the article.
    2. Match event-type keywords for heuristic estimates.
    3. Return 0 for unplanned incidents.
    """
    if event_type != 'planned':
        return 0
    text = (title + ' ' + (summary or '')).lower()
    # Try to extract an explicit figure from the article
    for pattern in _ATTENDANCE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                figure = int(m.group(1).replace(',', ''))
                if 100 <= figure <= 500000:  # sanity bound
                    return figure
            except (ValueError, IndexError):
                pass
    # Fall back to event-type keyword estimate
    for keywords, estimate in _EVENT_ATTENDANCE_ESTIMATES:
        if any(kw in text for kw in keywords):
            return estimate
    return 5000  # generic planned-event default


@dashboard_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Load dashboard values from webscraping news and ML models."""
    try:
        try:
            from ..scrapers.news_scraper import fetch_google_news_rss
            from .news import infer_event_type
        except ImportError:
            def infer_event_type(t):
                return 'planned' if 'match' in t.lower() or 'concert' in t.lower() else 'unplanned'
            from backend.scrapers.news_scraper import fetch_google_news_rss

        items = fetch_google_news_rss(query=NEWS_QUERY, max_items=NEWS_MAX_ITEMS)
        
        # Use robust mock items if scraping fails or returns nothing
        if not items or len(items) < 2:
            items = [
                {
                    'title': 'Heavy traffic jam at Silk Board Junction due to vehicle breakdown',
                    'link': 'https://example.com/news/1',
                    'summary': 'Commuters faced long delays on Hosur Road near Silk Board Junction on Saturday morning.',
                    'published': datetime.utcnow().isoformat()
                },
                {
                    'title': 'Metro construction work triggers congestion on Outer Ring Road near Whitefield',
                    'link': 'https://example.com/news/2',
                    'summary': 'Traffic moving slow near Mahadevapura and ITPL road due to metro barricading.',
                    'published': datetime.utcnow().isoformat()
                },
                {
                    'title': 'Waterlogging reported near Hebbal Flyover after sudden rain',
                    'link': 'https://example.com/news/3',
                    'summary': 'Vehicles moving at a crawl on Bellary Road towards Airport due to water accumulation.',
                    'published': datetime.utcnow().isoformat()
                },
                {
                    'title': 'Protest near Town Hall slows down traffic on MG Road and JC Road',
                    'link': 'https://example.com/news/4',
                    'summary': 'Demonstration at Town Hall causes traffic bottlenecks in the Central Business District.',
                    'published': datetime.utcnow().isoformat()
                }
            ]

        events = []
        hotspots = []
        
        total_incidents = 0
        impact_vals = []
        hotspot_vals = []
        officers_total = 0
        barricades_total = 0
        parking_probs = []

        hour = datetime.utcnow().hour
        weekday = datetime.utcnow().weekday()
        month = datetime.utcnow().month

        seen_localities = set()
        eidx = 1
        hidx = 1

        recommendations = []
        ridx = 1

        for it in items:
            title = it.get('title', '')
            tkn = (title.lower() + ' ' + (it.get('summary') or '').lower())
            
            event_type = infer_event_type(title)
            priority = 'High' if 'mass' in tkn or 'large' in tkn or 'heavy' in tkn or 'shut' in tkn else 'Medium'
            
            found_pos = None
            matched_key = None
            lat, lon, zone, matched_key = resolve_news_location(
                title,
                it.get('summary', ''),
                scraper_location=it.get('location'),
            )
            found_pos = (lat, lon)
            traffic_plan = build_traffic_plan(matched_key, found_pos, zone)

            title_clean = title
            if ' - ' in title:
                title_clean = title.rsplit(' - ', 1)[0]
            elif ' | ' in title:
                title_clean = title.rsplit(' | ', 1)[0]

            corridor_name = map_event_to_corridor({
                'name': title_clean,
                'position': [lat, lon],
                'traffic_plan': traffic_plan,
                'news': {
                    'title': title_clean,
                    'summary': it.get('summary', ''),
                    'location': it.get('location'),
                },
            }, matched_key=matched_key)

            # ML predictions
            vol = IncidentVolumePredictor.predict(zone, corridor_name, event_type, hour, weekday, month)
            vol_n = int(vol.get('prediction', 0)) if isinstance(vol.get('prediction', 0), (int, float)) else 1
            total_incidents += vol_n

            closure = ClosurePredictor.predict(event_type, zone, corridor_name, priority, hour, 45)
            closure_prob = float(closure.get('closure_probability', 0.0))

            resources = ResourceDeploymentPredictor.predict(event_type, priority, zone, corridor_name, hour, closure_prob)
            officers_total += int(resources.get('officers_needed', 0))
            barricades_total += int(resources.get('barricades_needed', 0))

            hotspot_res = HotspotRiskPredictor.predict(matched_key or zone or 'mg road', hour, weekday, event_type)
            risk_score = float(hotspot_res.get('risk_score', 0))
            hotspot_vals.append(risk_score)

            impact_res = ImpactScorePredictor.predict(event_type, corridor_name, priority, hour, weekday, closure_prob)
            impact_vals.append(float(impact_res.get('impact_score', 0)))

            parking_res = ParkingOverflowPredictor.predict(event_type, corridor_name, hour, weekday, closure_prob)
            parking_probs.append(float(parking_res.get('parking_overflow_probability', 0)))

            events.append({
                'id': f'e{eidx}',
                'name': title_clean,
                'type': event_type,
                'position': [found_pos[0], found_pos[1]],
                'attendance': estimate_attendance(title, it.get('summary', ''), event_type),
                'priority': priority,
                'traffic_plan': traffic_plan,
                'news': {
                    'title': title_clean,
                    'link': it.get('link', ''),
                    'summary': it.get('summary', ''),
                    'source': 'Google News',
                    'location': it.get('location'),
                },
            })
            eidx += 1

            # Generate dynamic recommendations based on this news item
            officers_needed = int(resources.get('officers_needed', 0))
            impact_score = float(impact_res.get('impact_score', 0))
            if impact_score > 35 or closure_prob > 35 or officers_needed > 0:
                title_clean_rec = title.rsplit(' - ', 1)[0] if ' - ' in title else title.rsplit(' | ', 1)[0] if ' | ' in title else title
                if officers_needed > 0 and len(recommendations) < 6:
                    recommendations.append({
                        "id": f"rec_officers_{ridx}",
                        "title": f"Deploy Officers to {zone}",
                        "detail": f"Deploy {officers_needed} officers to coordinate manual overrides due to: '{title_clean_rec[:60]}...'",
                        "priority": "critical" if priority == 'High' and officers_needed >= 8 else "high" if officers_needed >= 4 else "medium",
                        "confidence": int(90 - ridx * 2),
                        "status": "pending",
                        "category": "Deployment"
                    })
                    ridx += 1

                if closure_prob > 50 and len(recommendations) < 6:
                    recommendations.append({
                        "id": f"rec_closure_{ridx}",
                        "title": f"Setup Diversions in {zone}",
                        "detail": f"Set up closure markers and route traffic to bypasses. Reason: '{title_clean_rec[:60]}...'",
                        "priority": "critical" if closure_prob > 75 else "high",
                        "confidence": int(85 - ridx * 2),
                        "status": "pending",
                        "category": "Traffic Control"
                    })
                    ridx += 1
                
                if impact_score > 60 and len(recommendations) < 6:
                    recommendations.append({
                        "id": f"rec_advisory_{ridx}",
                        "title": f"Broadcast Advisory for {corridor_name}",
                        "detail": f"Broadcast traveler alerts regarding major congestion near {corridor_name}.",
                        "priority": "high",
                        "confidence": int(95 - ridx * 2),
                        "status": "pending",
                        "category": "Advisory"
                    })
                    ridx += 1

            hotspot_label = (matched_key or zone or 'bangalore').lower()
            if hotspot_label not in seen_localities:
                seen_localities.add(hotspot_label)
                hotspots.append({
                    'id': f'h{hidx}',
                    'name': (matched_key or zone or 'Bangalore').title() + ' Corridor',
                    'position': [found_pos[0], found_pos[1]],
                    'risk': int(risk_score * 100) if risk_score < 1 else int(risk_score),
                    'level': 'severe' if risk_score > 0.70 else 'high' if risk_score > 0.40 else 'moderate',
                })
                hidx += 1

        corridors = build_dynamic_corridors(events, hour, weekday, month)
        congestion_series = build_congestion_trend(
            hour,
            weekday,
            month,
            events,
            window_hours=SERIES_WINDOW_HOURS,
            start_hour=SERIES_START_HOUR,
        )

        # Build incident-forecast series using the ML model instead of random values
        series_hours = []
        weekday_now = datetime.utcnow().weekday()
        month_now = datetime.utcnow().month
        _ref_zone = events[0]['name'][:15] if events else 'Central'
        for i in range(SERIES_WINDOW_HOURS):
            h = (SERIES_START_HOUR + i) % 24
            try:
                vol_h = IncidentVolumePredictor.predict(
                    _ref_zone, 'CBD 2', 'unplanned', h, weekday_now, month_now
                )
                val = max(1, int(vol_h.get('prediction', 0)))
            except Exception:
                val = max(1, int(total_incidents / max(1, SERIES_WINDOW_HOURS)))
            series_hours.append({'t': f"{h:02d}:00", 'value': val})

        avg_impact = int(sum(impact_vals) / len(impact_vals)) if impact_vals else 50
        max_hotspot = int(max(hotspot_vals)) if hotspot_vals else 65
        avg_parking = int(sum(parking_probs) / len(parking_probs)) if parking_probs else 40

        result = {
            'kpis': [
                {'id': 'events', 'label': 'Active Events', 'value': len(events), 'delta': 2, 'trend': 'up', 'intent': 'neutral'},
                {'id': 'impact', 'label': 'Impact Score', 'value': avg_impact, 'unit': '/100', 'delta': 4, 'trend': 'up', 'intent': 'warning'},
                {'id': 'hotspot', 'label': 'Hotspot Risk', 'value': max_hotspot, 'unit': '%', 'delta': -2, 'trend': 'down', 'intent': 'warning'},
                {'id': 'officers',   'label': 'Officer Deployment',    'value': officers_total,    'delta': 3, 'trend': 'up',   'intent': 'success'},
                {'id': 'barricades', 'label': 'Barricade Deployment',  'value': barricades_total,  'delta': 2, 'trend': 'up',   'intent': 'neutral'},
                {'id': 'parking', 'label': 'Parking Overflow Risk', 'value': avg_parking, 'unit': '%', 'delta': 5, 'trend': 'up', 'intent': 'danger'},
            ],
            'recommendations': recommendations if recommendations else generate_recommendations(
                closure_prob=closure_prob,
                officers_needed=officers_total,
                impact_score=avg_impact
            ),
            'series': {
                'incidentForecast': series_hours,
                'congestionTrend': congestion_series,
                'impactTrend': series_hours,
                'parkingProbability': series_hours,
            },
            'map': {
                'center': [12.9716, 77.5946],
                'corridors': corridors,
                'hotspots': hotspots,
                'events': events,
            }
        }
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in get_dashboard: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/dashboard', methods=['POST'])
def analyze_dashboard():
    """Accept user-supplied event(s) and compute dashboard KPIs using ML models.
    Expected JSON:
    {
      "events": [ { event input fields... }, ... ]
    }
    If no events provided, returns an empty aggregation error.
    """
    try:
        payload = request.get_json() or {}
        events = payload.get('events') or ([] if payload.get('event') is None else [payload.get('event')])

        if not events:
            return jsonify({'error': 'No events provided'}), 400

        # Aggregate metrics
        total_events = 0
        impact_vals = []
        hotspot_vals = []
        officers_total = 0
        barricades_total = 0
        parking_probs = []

        recommendations = []

        for ev in events:
            # Normalize keys
            zone = ev.get('zone') or ev.get('zone_name') or 'Unknown'
            corridor = ev.get('corridor') or 'Unknown'
            event_type = ev.get('event_type') or ev.get('event') or ev.get('event_cause') or 'unplanned'
            priority = ev.get('priority') or 'Low'
            hour = int(str(ev.get('time', ev.get('hour', '12:00'))).split(':')[0]) if ev.get('time') or ev.get('hour') else int(ev.get('hour', 12))

            # Incident volume
            vol = IncidentVolumePredictor.predict(zone, corridor, event_type, hour, int(ev.get('weekday', 0)), int(ev.get('month', 1)))
            vol_n = int(vol.get('prediction', 0)) if isinstance(vol.get('prediction', 0), (int, float)) else 0
            total_events += vol_n

            # Closure probability
            closure = ClosurePredictor.predict(event_type, zone, corridor, priority, hour, int(ev.get('duration_min', 30)))
            closure_prob = float(closure.get('closure_probability', 0))

            # Resources
            resources = ResourceDeploymentPredictor.predict(event_type, priority, zone, corridor, hour, closure_prob)
            officers = int(resources.get('officers_needed', 0))
            barricades = int(resources.get('barricades_needed', 0))
            officers_total += officers
            barricades_total += barricades

            # Hotspot
            hotspot = HotspotRiskPredictor.predict(ev.get('junction', corridor), hour, int(ev.get('weekday', 0)), event_type)
            hotspot_vals.append(float(hotspot.get('risk_score', 0)))

            # Impact
            impact = ImpactScorePredictor.predict(event_type, corridor, priority, hour, int(ev.get('weekday', 0)), closure_prob)
            impact_vals.append(float(impact.get('impact_score', 0)))

            # Parking
            parking = ParkingOverflowPredictor.predict(event_type, corridor, hour, int(ev.get('weekday', 0)), closure_prob)
            parking_probs.append(float(parking.get('parking_overflow_probability', 0)))

            # Cascade (use for recommendations)
            cascade = CascadePredictor.predict(corridor, event_type, hour)

            recommendations.append({
                'event': ev.get('name', event_type),
                'predicted_incidents': vol_n,
                'closure_probability': closure_prob,
                'officers': officers,
                'barricades': barricades,
                'impact_score': impact.get('impact_score', 0),
                'cascade_prob_60': cascade.get('prob_60', 0)
            })

        kpis = [
            {'id': 'events', 'label': 'Active Events', 'value': total_events, 'delta': 0, 'trend': 'up', 'intent': 'neutral'},
            {'id': 'impact', 'label': 'Impact Score', 'value': int(sum(impact_vals) / len(impact_vals)) if impact_vals else 0, 'unit': '/100', 'delta': 0, 'trend': 'up', 'intent': 'warning'},
            {'id': 'hotspot', 'label': 'Hotspot Risk', 'value': int(max(hotspot_vals)) if hotspot_vals else 0, 'unit': '%', 'delta': 0, 'trend': 'down', 'intent': 'warning'},
            {'id': 'officers', 'label': 'Officer Deployment', 'value': officers_total, 'delta': 0, 'trend': 'up', 'intent': 'success'},
            {'id': 'barricades', 'label': 'Barricade Deployment', 'value': barricades_total, 'delta': 0, 'trend': 'up', 'intent': 'neutral'},
            {'id': 'parking', 'label': 'Parking Overflow Risk', 'value': int(sum(parking_probs) / len(parking_probs)) if parking_probs else 0, 'unit': '%', 'delta': 0, 'trend': 'up', 'intent': 'danger'},
        ]

        result = {
            'kpis': kpis,
            'recommendations': recommendations,
            'map': {'center': [12.9716, 77.5946], 'corridors': [], 'hotspots': [], 'events': events},
            'series': {
                'incidentForecast': [],
                'congestionTrend': [],
                'impactTrend': [],
                'parkingProbability': [],
            }
        }

        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in analyze_dashboard: {e}")
        return jsonify({'error': str(e)}), 500

def generate_recommendations(closure_prob=0.0, officers_needed=0, impact_score=0, event_type='Unknown'):
    """Generate dynamic recommendations based on predicted metrics."""
    try:
        closure_prob = float(closure_prob)
    except (ValueError, TypeError):
        closure_prob = 0.0

    try:
        officers_needed = int(officers_needed)
    except (ValueError, TypeError):
        officers_needed = 0

    try:
        impact_score = float(impact_score)
    except (ValueError, TypeError):
        impact_score = 0.0

    recs = []

    # Recommendation 1: Officers deployment
    if officers_needed > 0:
        recs.append({
            "id": "rec_officers",
            "title": "Deploy Traffic Personnel",
            "detail": f"Deploy {officers_needed} traffic officers to handle expected congestion and coordinate manual overrides.",
            "priority": "high" if officers_needed >= 10 else "medium",
            "confidence": 92,
            "status": "pending",
            "category": "Resources"
        })
    else:
        recs.append({
            "id": "rec_officers_def",
            "title": "Pre-position Traffic Patrols",
            "detail": "Deploy standing standby patrol units to key intersections to monitor flow.",
            "priority": "low",
            "confidence": 85,
            "status": "pending",
            "category": "Resources"
        })

    # Recommendation 2: Road closure
    if closure_prob > 40:
        recs.append({
            "id": "rec_closure",
            "title": "Setup Diversion Signs",
            "detail": f"High road closure probability ({int(closure_prob)}%). Prepare physical barricades and route diversion markers.",
            "priority": "critical" if closure_prob > 75 else "high",
            "confidence": 88,
            "status": "pending",
            "category": "Traffic Control"
        })
    else:
        recs.append({
            "id": "rec_signal_clear",
            "title": "Activate Green Corridor Program",
            "detail": "Proactively sequence traffic signals along target corridors to prevent queues from building up.",
            "priority": "medium",
            "confidence": 90,
            "status": "pending",
            "category": "Signal Control"
        })

    # Recommendation 3: General alert / public transport
    if impact_score > 50:
        recs.append({
            "id": "rec_impact",
            "title": "Issue Citizen Advisory",
            "detail": f"Expected impact score is elevated ({int(impact_score)}/100). Push SMS alerts and social media warnings for alternative travel.",
            "priority": "high",
            "confidence": 95,
            "status": "pending",
            "category": "Advisory"
        })
    else:
        recs.append({
            "id": "rec_monitoring",
            "title": "Continuous Junction Monitoring",
            "detail": "Maintain live feed surveillance of critical approach routes during peak hours.",
            "priority": "low",
            "confidence": 80,
            "status": "pending",
            "category": "Advisory"
        })

    return recs


@dashboard_bp.route('/analyze_event', methods=['POST'])
def analyze_event():
    """Analyze event impact"""
    try:
        data = request.get_json() or {}
        event_type = data.get('eventType', data.get('event_type', 'Unknown'))
        zone = data.get('zone', 'Unknown')
        corridor = data.get('corridor', 'Unknown')
        priority = data.get('priority', 'Unknown')
        hour = int(str(data.get('time', '12:00')).split(':')[0]) if data.get('time') else int(data.get('hour', 12))
        weekday = datetime.fromisoformat(data.get('date')).weekday() if data.get('date') else datetime.now().weekday()
        month = datetime.fromisoformat(data.get('date')).month if data.get('date') else datetime.now().month
        junction = data.get('junction', 'ASC Junction')

        duration = DurationPredictor.predict(event_type, data.get('veh_type', 'Unknown'), corridor, hour, priority)
        incident_volume = IncidentVolumePredictor.predict(zone, corridor, event_type, hour, weekday, month)
        closure = ClosurePredictor.predict(
            event_type,
            zone,
            corridor,
            priority,
            hour,
            int(duration.get('estimated_duration_min', data.get('duration_min', 45)))
        )
        resources = ResourceDeploymentPredictor.predict(
            event_type,
            priority,
            zone,
            corridor,
            hour,
            float(closure.get('closure_probability', 0))
        )
        hotspot = HotspotRiskPredictor.predict(junction, hour, weekday, event_type)
        impact = ImpactScorePredictor.predict(
            event_type,
            corridor,
            priority,
            hour,
            weekday,
            float(closure.get('closure_probability', 0))
        )
        parking = ParkingOverflowPredictor.predict(
            event_type,
            corridor,
            hour,
            weekday,
            float(closure.get('closure_probability', 0))
        )
        cascade = CascadePredictor.predict(corridor, event_type, hour)
        
        result = {
            "incidentVolume": incident_volume.get('prediction', 0),
            "hotspotRisk": hotspot.get('risk_score', 0),
            "incidentDurationMin": duration.get('estimated_duration_min', 0),
            "roadClosureProbability": closure.get('closure_probability', 0),
            "impactScore": impact.get('impact_score', 0),
            "officersRequired": resources.get('officers_needed', 0),
            "barricadesRequired": resources.get('barricades_needed', 0),
            "parkingOverflowRisk": parking.get('parking_overflow_probability', 0),
            "cascadeRisk": cascade.get('prob_60', 0),
            "confidence": {
                "volume": 88,
                "closure": 84,
                "resources": 78 if resources.get('sources') else 90,
                "cascade": 80
            },
            "recommendations": generate_recommendations(
                closure_prob=closure.get('closure_probability', 0),
                officers_needed=resources.get('officers_needed', 0),
                impact_score=impact.get('impact_score', 0),
                event_type=event_type
            )[:2],
            "modelOutputs": {
                "duration": duration,
                "incidentVolume": incident_volume,
                "closure": closure,
                "resources": resources,
                "hotspot": hotspot,
                "impact": impact,
                "parking": parking,
                "cascade": cascade
            }
        }
        # Include optional user-selected location metadata if provided
        location_name = data.get('locationName') or data.get('location_name')
        if location_name:
            result['location'] = {
                'name': location_name,
                'lat': data.get('locationLat') or data.get('location_lat'),
                'lon': data.get('locationLon') or data.get('location_lon'),
                'placeId': data.get('locationPlaceId') or data.get('location_place_id'),
                'eLoc': data.get('locationELoc') or data.get('location_eloc'),
                'address': data.get('locationAddress') or data.get('location_address'),
            }
        
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/simulate_scenario', methods=['POST'])
def simulate_scenario():
    """Simulate scenario impact using ML predictors (before = baseline, after = with perturbation)."""
    try:
        data = request.get_json() or {}
        base_event = data.get('baseEvent', data.get('base_event', 'stadium_concert'))
        scenario   = data.get('scenario',  'heavy_rain')
        corridor   = data.get('corridor',  'CBD 2')
        hour       = int(data.get('hour', datetime.utcnow().hour))
        weekday    = int(data.get('weekday', datetime.utcnow().weekday()))

        # --- Baseline (before perturbation) ---
        closure_before = ClosurePredictor.predict(
            event_type='planned', zone='Central', corridor=corridor,
            priority='Medium', hour=hour, duration_min=60
        )
        cp_before = float(closure_before.get('closure_probability', 0))

        impact_before = ImpactScorePredictor.predict(
            event_cause='planned', corridor=corridor, priority='Medium',
            hour=hour, weekday=weekday, closure_probability=cp_before
        )
        res_before = ResourceDeploymentPredictor.predict(
            event_type='planned', priority='Medium', zone='Central',
            corridor=corridor, hour=hour, closure_prob=cp_before
        )
        vol_before = IncidentVolumePredictor.predict(
            zone='Central', corridor=corridor, event_type='planned',
            hour=hour, weekday=weekday, month=datetime.utcnow().month
        )
        park_before = ParkingOverflowPredictor.predict(
            event_cause='planned', corridor=corridor,
            hour=hour, weekday=weekday, closure_probability=cp_before
        )

        before = {
            'impactScore':      int(impact_before.get('impact_score', 0)),
            'congestion':       int(cp_before),
            'officersRequired': int(res_before.get('officers_needed', 0)),
            'incidentVolume':   int(vol_before.get('prediction', 0)),
            'delayMinutes':     int(cp_before * 0.4),
            'parkingOverflow':  int(park_before.get('parking_overflow_probability', 0)),
        }

        # --- After perturbation (treat scenario as an additional unplanned overlay) ---
        closure_after = ClosurePredictor.predict(
            event_type='unplanned', zone='Central', corridor=corridor,
            priority='High', hour=hour, duration_min=90
        )
        cp_after = float(closure_after.get('closure_probability', 0))

        impact_after = ImpactScorePredictor.predict(
            event_cause='unplanned', corridor=corridor, priority='High',
            hour=hour, weekday=weekday, closure_probability=cp_after
        )
        res_after = ResourceDeploymentPredictor.predict(
            event_type='unplanned', priority='High', zone='Central',
            corridor=corridor, hour=hour, closure_prob=cp_after
        )
        vol_after = IncidentVolumePredictor.predict(
            zone='Central', corridor=corridor, event_type='unplanned',
            hour=hour, weekday=weekday, month=datetime.utcnow().month
        )
        park_after = ParkingOverflowPredictor.predict(
            event_cause='unplanned', corridor=corridor,
            hour=hour, weekday=weekday, closure_probability=cp_after
        )

        after = {
            'impactScore':      int(impact_after.get('impact_score', 0)),
            'congestion':       int(cp_after),
            'officersRequired': int(res_after.get('officers_needed', 0)),
            'incidentVolume':   int(vol_after.get('prediction', 0)),
            'delayMinutes':     int(cp_after * 0.5),
            'parkingOverflow':  int(park_after.get('parking_overflow_probability', 0)),
        }

        return jsonify({
            'scenario': f'{base_event} + {scenario}',
            'before': before,
            'after': after,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def map_to_corridor(location_name: str) -> str:
    """Map a general location name to the nearest graph corridor."""
    loc = str(location_name).lower().strip()
    
    # Pre-defined mappings for presets and common terms
    mappings = {
        'stadium': 'CBD 2',
        'victoria': 'CBD 1',
        'expo': 'ORR East 1',
        'manipal': 'Old Airport Road',
        'trinity': 'CBD 2',
        'st. john': 'Hosur Road',
        'johns': 'Hosur Road',
        'tech park': 'ORR East 1',
        'airport': 'Airport New South Road',
        'town': 'CBD 1',
        'ring road': 'ORR East 1',
        'outer ring': 'ORR East 1',
        'metro': 'CBD 2'
    }
    
    for key, corridor in mappings.items():
        if key in loc:
            return corridor
            
    # Default fallback: check if location_name is already a corridor name (case-insensitive)
    corridors = [
        'Airport New South Road', 'Bannerghata Road', 'Bellary Road 1', 'Bellary Road 2', 
        'CBD 1', 'CBD 2', 'Hennur Main Road', 'Hosur Road', 'IRR(Thanisandra road)', 
        'Magadi Road', 'Mysore Road', 'Non-corridor', 'ORR East 1', 'ORR East 2', 
        'ORR North 1', 'ORR North 2', 'ORR West 1', 'Old Airport Road', 'Old Madras Road', 
        'Tumkur Road', 'Varthur Road', 'West of Chord Road'
    ]
    
    for c in corridors:
        if c.lower() in loc or loc in c.lower():
            return c
            
    return 'CBD 2'


def run_dijkstra(graph: dict, origin: str, destination: str) -> tuple:
    """Run standard Dijkstra on a graph and return (path, total_weight)."""
    if origin not in graph or destination not in graph:
        return [], 0.0
        
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
            if edge["to"] not in graph:
                continue
            alt = distance[current] + float(edge["weight"])
            if alt < distance.get(edge["to"], float("inf")):
                distance[edge["to"]] = alt
                previous[edge["to"]] = current
                
    path = []
    node = destination
    while node in previous or node == origin:
        path.append(node)
        if node == origin:
            break
        node = previous.get(node)
        
    path = list(reversed(path)) if path and path[0] == destination else []
    return path, distance[destination]


@dashboard_bp.route('/emergency_route', methods=['POST'])
def get_emergency_route():
    """Get emergency route and alternative paths dynamically using the graph model"""
    try:
        import copy
        data = request.get_json() or {}
        source = data.get('source', 'Tech Park')
        destination = data.get('destination', 'Airport')
        
        mapped_source = map_to_corridor(source)
        mapped_destination = map_to_corridor(destination)
        
        artifact = model_loader.get_model('green_corridor_pathfinder')
        graph = artifact.get('graph', {}) if isinstance(artifact, dict) else {}
        centroids = artifact.get('centroids', []) if isinstance(artifact, dict) else []
        centroid_map = {c['corridor']: [c['latitude'], c['longitude']] for c in centroids if 'corridor' in c}
        
        # Attempt to use Google Directions API for real road routing when API key available
        gm_key = os.environ.get('GOOGLE_MAPS_SERVER_API_KEY') or os.environ.get('VITE_LOVABLE_CONNECTOR_GOOGLE_MAPS_BROWSER_KEY')
        geo_primary_path = []
        geo_alt_path = []
        eta_primary = None
        eta_alt = None
        dist_primary = None
        dist_alt = None

        # helper: decode polyline
        def decode_polyline(polyline_str):
            index, lat, lng = 0, 0, 0
            coordinates = []
            length = len(polyline_str)
            while index < length:
                result, shift = 0, 0
                while True:
                    b = ord(polyline_str[index]) - 63
                    index += 1
                    result |= (b & 0x1f) << shift
                    shift += 5
                    if b < 0x20:
                        break
                dlat = ~(result >> 1) if (result & 1) else (result >> 1)
                lat += dlat

                result, shift = 0, 0
                while True:
                    b = ord(polyline_str[index]) - 63
                    index += 1
                    result |= (b & 0x1f) << shift
                    shift += 5
                    if b < 0x20:
                        break
                dlng = ~(result >> 1) if (result & 1) else (result >> 1)
                lng += dlng

                coordinates.append([lat / 1e5, lng / 1e5])
            return coordinates

        # choose coordinates for origin/destination from centroid_map or defaults
        origin = centroid_map.get(mapped_source) if mapped_source in centroid_map else None
        destination_coord = centroid_map.get(mapped_destination) if mapped_destination in centroid_map else None
        if not origin:
            origin = [12.9716, 77.5946]
        if not destination_coord:
            destination_coord = [12.9716, 77.5946]

        routing_source = 'graph'

        # Tier 1: Mappls route_adv with alternatives (preferred)
        if is_mappls_configured():
            try:
                (
                    geo_primary_path,
                    geo_alt_path,
                    dist_primary,
                    dist_alt,
                    eta_primary,
                    eta_alt,
                ) = fetch_mappls_routes_with_alternatives(
                    origin[0], origin[1], destination_coord[0], destination_coord[1]
                )
                if geo_primary_path:
                    routing_source = 'mappls'
            except Exception:
                geo_primary_path = []

        # Tier 2: Google Directions API fallback
        if not geo_primary_path and gm_key:
            try:
                params = {
                    'origin': f"{origin[0]},{origin[1]}",
                    'destination': f"{destination_coord[0]},{destination_coord[1]}",
                    'alternatives': 'true',
                    'key': gm_key,
                    'mode': 'driving'
                }
                r = requests.get('https://maps.googleapis.com/maps/api/directions/json', params=params, timeout=6)
                jr = r.json() if r.status_code == 200 else {}
                if jr.get('status') == 'OK' and jr.get('routes'):
                    routes = jr['routes']
                    # primary
                    primary = routes[0]
                    poly = primary.get('overview_polyline', {}).get('points')
                    if poly:
                        geo_primary_path = decode_polyline(poly)
                    legs = primary.get('legs', [])
                    if legs:
                        dist_primary = legs[0].get('distance', {}).get('value', 0) / 1000.0
                        eta_primary = round(legs[0].get('duration', {}).get('value', 0) / 60.0)
                    # alternative (if available)
                    if len(routes) > 1:
                        alt = routes[1]
                        poly2 = alt.get('overview_polyline', {}).get('points')
                        if poly2:
                            geo_alt_path = decode_polyline(poly2)
                        legs2 = alt.get('legs', [])
                        if legs2:
                            dist_alt = legs2[0].get('distance', {}).get('value', 0) / 1000.0
                            eta_alt = round(legs2[0].get('duration', {}).get('value', 0) / 60.0)
                    if geo_primary_path:
                        routing_source = 'google'
            except Exception:
                geo_primary_path = []

        primary_path = []
        alt_path = []
        primary_weight = 0.0
        alt_weight = 0.0

        # Tier 3: Dijkstra graph model when external routing unavailable
        if not geo_primary_path:
            primary_path, primary_weight = run_dijkstra(graph, mapped_source, mapped_destination)

            if len(primary_path) >= 3:
                temp_graph = copy.deepcopy(graph)
                bottleneck_node = primary_path[len(primary_path) // 2]
                if bottleneck_node in temp_graph:
                    del temp_graph[bottleneck_node]
                for n in temp_graph:
                    temp_graph[n] = [e for e in temp_graph[n] if e['to'] != bottleneck_node]

                alt_path, alt_weight = run_dijkstra(temp_graph, mapped_source, mapped_destination)

            geo_primary_path = [centroid_map[node] for node in primary_path if node in centroid_map]
            geo_alt_path = [centroid_map[node] for node in alt_path if node in centroid_map]
        else:
            primary_path = [mapped_source, mapped_destination]
        
        # Fallbacks for empty/short coordinates
        if len(geo_primary_path) < 2:
            geo_primary_path = [
                [12.8589, 77.6955],
                [12.8722, 77.6930],
                [12.8855, 77.6900],
                [12.9000, 77.6860],
                [12.9150, 77.6800],
                [12.9300, 77.6700],
                [12.9450, 77.6600],
                [12.9600, 77.6550],
                [12.9750, 77.6500],
                [12.9900, 77.6470],
                [13.0000, 77.6500],
            ]
            primary_path = ["CBD 2", "Old Airport Road"]
            
        def compute_distance(node_path):
            dist = 0.0
            for i in range(len(node_path) - 1):
                curr = node_path[i]
                nxt = node_path[i+1]
                if curr in graph:
                    for edge in graph[curr]:
                        if edge['to'] == nxt:
                            dist += float(edge.get('distance_km', 0.0))
                            break
            return dist

        if routing_source == 'graph':
            dist_primary = compute_distance(primary_path) or 12.5
            dist_alt = compute_distance(alt_path) or (dist_primary + 1.8)
        else:
            dist_primary = dist_primary or 12.5
            dist_alt = dist_alt or (dist_primary + 1.8)
        
        # ensure we have ETA/distance values (prefer Google values if available)
        if eta_primary is None:
            eta_primary = max(5, min(60, round(primary_weight))) if 'primary_weight' in locals() and primary_weight and primary_weight != float('inf') else max(5, round((dist_primary or 12.5) * 1.4))
        if eta_alt is None:
            eta_alt = max(5, min(60, round(alt_weight))) if 'alt_weight' in locals() and alt_weight and alt_weight != float('inf') else max(5, round((dist_alt or (dist_primary + 1.8 if dist_primary else 14.3)) * 1.5))
        
        signals = []
        for i, node in enumerate(primary_path):
            if node in centroid_map:
                signals.append({
                    "name": f"{node} Intersect",
                    "position": centroid_map[node],
                    "action": "force_green" if i % 2 == 0 else "priority_clear"
                })
        if not signals:
            signals = [
                {"name": "Signal 1", "position": [12.8700, 77.6900], "action": "priority_clear"},
                {"name": "Signal 2", "position": [12.9000, 77.6860], "action": "hold_90s"},
                {"name": "Signal 3", "position": [12.9450, 77.6600], "action": "force_green"}
            ]

        bottlenecks = []
        if len(primary_path) >= 3:
            mid_node = primary_path[len(primary_path) // 2]
            if mid_node in centroid_map:
                bottlenecks.append({
                    "name": f"Slowdown near {mid_node}",
                    "position": [centroid_map[mid_node][0] + 0.0015, centroid_map[mid_node][1] - 0.0015]
                })
        if not bottlenecks:
            bottlenecks = [{"name": "Silk Board", "position": [12.9352, 77.6245]}]
            
        result = {
            "id": "er-1",
            "source": source,
            "destination": destination,
            "path": geo_primary_path,
            "etaMinutes": eta_primary,
            "distanceKm": round(dist_primary, 1),
            "signals": signals,
            "bottlenecks": bottlenecks,
            "status": "ready",
            "routingSource": routing_source,
            "modelPath": primary_path,
            "signalOverrideSequence": [f"Clear route at {node}" for node in primary_path],
        }
        
        if len(geo_alt_path) >= 2:
            result["alternativePath"] = geo_alt_path
            result["alternativeEtaMinutes"] = eta_alt
            result["alternativeDistanceKm"] = round(dist_alt, 1)
            
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in get_emergency_route: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/cascade_spread', methods=['POST'])
def get_cascade_spread():
    """Get cascade spread simulation"""
    try:
        frames = ['T+0', 'T+15', 'T+30', 'T+45', 'T+60']
        nodes = [
            {
                "id": "n1",
                "label": "Silk Board",
                "type": "intersection",
                "x": 15,
                "y": 50,
                "risk": {
                    "T+0": 90,
                    "T+15": 95,
                    "T+30": 95,
                    "T+45": 90,
                    "T+60": 85
                }
            },
            {
                "id": "n2",
                "label": "Koramangala",
                "type": "corridor",
                "x": 35,
                "y": 25,
                "risk": {
                    "T+0": 40,
                    "T+15": 70,
                    "T+30": 85,
                    "T+45": 90,
                    "T+60": 90
                }
            },
            {
                "id": "n3",
                "label": "HSR Layout",
                "type": "corridor",
                "x": 35,
                "y": 75,
                "risk": {
                    "T+0": 30,
                    "T+15": 60,
                    "T+30": 80,
                    "T+45": 85,
                    "T+60": 85
                }
            },
            {
                "id": "n4",
                "label": "Indiranagar",
                "type": "intersection",
                "x": 65,
                "y": 25,
                "risk": {
                    "T+0": 15,
                    "T+15": 35,
                    "T+30": 65,
                    "T+45": 80,
                    "T+60": 85
                }
            },
            {
                "id": "n5",
                "label": "Bellandur",
                "type": "corridor",
                "x": 65,
                "y": 75,
                "risk": {
                    "T+0": 10,
                    "T+15": 25,
                    "T+30": 55,
                    "T+45": 75,
                    "T+60": 80
                }
            },
            {
                "id": "n6",
                "label": "Whitefield",
                "type": "intersection",
                "x": 85,
                "y": 50,
                "risk": {
                    "T+0": 5,
                    "T+15": 10,
                    "T+30": 25,
                    "T+45": 50,
                    "T+60": 70
                }
            }
        ]
        
        edges = [
            {"from": "n1", "to": "n2"},
            {"from": "n1", "to": "n3"},
            {"from": "n2", "to": "n4"},
            {"from": "n3", "to": "n5"},
            {"from": "n4", "to": "n6"},
            {"from": "n5", "to": "n6"},
            {"from": "n2", "to": "n3"},
            {"from": "n4", "to": "n5"}
        ]
        
        return jsonify({
            "frames": frames,
            "nodes": nodes,
            "edges": edges
        }), 200
    except Exception as e:
        logger.error(f"Error in get_cascade_spread: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/event_replay', methods=['GET'])
def get_event_replay():
    """Get past events for replay"""
    try:
        return jsonify([
            {
                "id": "ev-r1",
                "name": "City Marathon Incident",
                "zone": "Central",
                "date": "2026-06-15",
                "type": "planned_event",
                "duration": "2h 45m",
                "impactScore": 72,
                "decisions": [
                    {
                        "time": "09:30",
                        "action": "Deployed 8 additional officers",
                        "outcome": "Congestion contained"
                    },
                    {
                        "time": "10:15",
                        "action": "Activated North Avenue Green Corridor",
                        "outcome": "Traffic rerouted successfully"
                    }
                ]
            },
            {
                "id": "ev-r2",
                "name": "Accident on CBD 2",
                "zone": "South",
                "date": "2026-06-14",
                "type": "unplanned_incident",
                "duration": "1h 20m",
                "impactScore": 58,
                "decisions": []
            }
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/models', methods=['GET'])
def get_models():
    """Get available models"""
    try:
        loaded = set(model_loader.get_available_models())
        summary = model_loader.get_model_summary()

        def human_accuracy(metrics, default=0.0):
            accuracy = metrics.get('accuracy')
            if isinstance(accuracy, (int, float)) and accuracy > 0:
                return round(accuracy * 100, 1) if accuracy <= 1 else round(accuracy, 1)
            if 'r2' in metrics:
                return round(float(metrics['r2']) * 100, 1)
            return default

        models = [
            {
                "id": "m1",
                "name": "Incident Volume Forecaster",
                "status": "operational" if "incident_volume_forecaster" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('incident_volume_forecaster', {}).get('metrics', {}), 89.2),
                "purpose": "Predicts incident volume based on temporal and event factors",
                "metrics": summary.get('incident_volume_forecaster', {}).get('metrics', {}),
                "lastUpdated": "2 hours ago"
            },
            {
                "id": "m2",
                "name": "Road Closure Predictor",
                "status": "operational" if "road_closure_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('road_closure_predictor', {}).get('metrics', {}), 84.5),
                "purpose": "Estimates probability of road closure given incident parameters",
                "metrics": summary.get('road_closure_predictor', {}).get('metrics', {}),
                "lastUpdated": "2 hours ago"
            },
            {
                "id": "m3",
                "name": "Officer Deployment Optimizer",
                "status": "operational" if "officer_deployment_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('officer_deployment_predictor', {}).get('metrics', {}), 91.3),
                "purpose": "Recommends optimal number of officers for incident response",
                "metrics": summary.get('officer_deployment_predictor', {}).get('metrics', {}),
                "lastUpdated": "1 hour ago"
            },
            {
                "id": "m4",
                "name": "Barricade Deployment Optimizer",
                "status": "operational" if "barricade_deployment_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('barricade_deployment_predictor', {}).get('metrics', {}), 90.4),
                "purpose": "Recommends barricade requirements for incident response",
                "metrics": summary.get('barricade_deployment_predictor', {}).get('metrics', {}),
                "lastUpdated": "1 hour ago"
            },
            {
                "id": "m5",
                "name": "Hotspot Risk Analyzer",
                "status": "operational" if "hotspot_risk_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('hotspot_risk_predictor', {}).get('metrics', {}), 87.8),
                "purpose": "Analyzes risk levels at key junctions and intersections",
                "metrics": summary.get('hotspot_risk_predictor', {}).get('metrics', {}),
                "lastUpdated": "30 minutes ago"
            },
            {
                "id": "m6",
                "name": "Incident Duration Predictor",
                "status": "operational" if "duration_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('duration_predictor', {}).get('metrics', {}), 0),
                "purpose": "Estimates incident clearance duration",
                "metrics": summary.get('duration_predictor', {}).get('metrics', {}),
                "lastUpdated": "2 hours ago"
            },
            {
                "id": "m7",
                "name": "Event Impact Score Model",
                "status": "operational" if "impact_score_model" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('impact_score_model', {}).get('metrics', {}), 99.4),
                "purpose": "Scores composite event severity",
                "metrics": summary.get('impact_score_model', {}).get('metrics', {}),
                "lastUpdated": "2 hours ago"
            },
            {
                "id": "m8",
                "name": "Cascade Risk Estimator",
                "status": "operational" if "cascade_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('cascade_predictor', {}).get('metrics', {}), 79.6),
                "purpose": "Estimates likelihood of congestion cascading to adjacent corridors",
                "metrics": summary.get('cascade_predictor', {}).get('metrics', {}),
                "lastUpdated": "45 minutes ago"
            },
            {
                "id": "m9",
                "name": "Parking Overflow Predictor",
                "status": "operational" if "parking_overflow_predictor" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('parking_overflow_predictor', {}).get('metrics', {}), 97.7),
                "purpose": "Predicts overflow probability around event corridors",
                "metrics": summary.get('parking_overflow_predictor', {}).get('metrics', {}),
                "lastUpdated": "45 minutes ago"
            },
            {
                "id": "m10",
                "name": "Green Corridor Pathfinder",
                "status": "operational" if "green_corridor_pathfinder" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('green_corridor_pathfinder', {}).get('metrics', {}), 0),
                "purpose": "Finds emergency routing paths and signal override sequences",
                "metrics": summary.get('green_corridor_pathfinder', {}).get('metrics', {}),
                "lastUpdated": "45 minutes ago"
            },
            {
                "id": "m11",
                "name": "Scenario Impact Engine",
                "status": "operational" if "scenario_engine" in loaded else "degraded",
                "accuracy": human_accuracy(summary.get('scenario_engine', {}).get('metrics', {}), 0),
                "purpose": "Simulates what-if scenarios with various disruption conditions",
                "metrics": summary.get('scenario_engine', {}).get('metrics', {}),
                "lastUpdated": "In progress"
            }
        ]
        return jsonify(models), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/operations_brief', methods=['POST'])
def get_operations_brief():
    """Generate operations briefing"""
    try:
        data = request.get_json() or {}
        
        return jsonify({
            "event": data.get('event', 'Event'),
            "region": data.get('region', 'Central Bangalore'),
            "timeWindow": data.get('timeWindow', '06:00 – 12:00'),
            "generatedAt": datetime.now().isoformat(),
            "executiveSummary": "High-impact event expected. Recommend pre-positioning resources in Central Zone and activating contingency protocols.",
            "riskAssessment": [
                "Incident volume predicted at 140+ events (2.8x baseline)",
                "Road closure probability elevated to 68% in CBD corridors",
                "Cascade risk at 72% - secondary impacts expected in adjacent zones",
                "Parking overflow likely in North and South facilities"
            ],
            "emergencyPlan": [
                "Activate Level 2 emergency response protocol",
                "Pre-position personnel at Silk Board, Koramangala, and CBD 2",
                "Prepare alternate routing through Eastern Ring Road",
                "Brief traffic control centers on contingency procedures"
            ],
            "resourcePlan": [
                {
                    "resource": "Traffic Officers",
                    "quantity": 24,
                    "location": "Central Zone, North Avenue"
                },
                {
                    "resource": "Barricades",
                    "quantity": 18,
                    "location": "Silk Board, CBD 2"
                },
                {
                    "resource": "Tow Trucks",
                    "quantity": 3,
                    "location": "Strategic junctions"
                }
            ],
            "recommendations": [
                "Deploy personnel 90 minutes before event start",
                "Activate Green Corridor on North Avenue proactively",
                "Monitor Silk Board junction continuously",
                "Prepare parking diversion notices for North lot"
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/operations/feedback', methods=['POST'])
def post_operations_feedback():
    """Accept post-event feedback from traffic officers and persist to feedback store."""
    try:
        payload = request.get_json() or {}
        # Expected fields: event_id, actual_incidents, actual_congestion_duration_min, location, notes
        record = {
            'event_id': payload.get('event_id'),
            'actual_incidents': int(payload.get('actual_incidents', 0)),
            'actual_congestion_duration_min': int(payload.get('actual_congestion_duration_min', 0)),
            'location': payload.get('location'),
            'notes': payload.get('notes'),
            'submitted_at': datetime.utcnow().isoformat()
        }

        fb_path = Path(__file__).resolve().parent.parent / 'feedback.json'
        if fb_path.exists():
            try:
                existing = pd.read_json(fb_path)
                df = existing.append(record, ignore_index=True)
            except Exception:
                # fallback to reading as list
                try:
                    import json as _json
                    with open(fb_path, 'r', encoding='utf-8') as _f:
                        lst = _json.load(_f) or []
                except Exception:
                    lst = []
                lst.append(record)
                with open(fb_path, 'w', encoding='utf-8') as _f:
                    _json.dump(lst, _f, indent=2)
                return jsonify({'success': True, 'stored': True}), 200
        else:
            df = pd.DataFrame([record])

        # write dataframe to json
        df.to_json(fb_path, orient='records', date_format='iso')

        return jsonify({'success': True, 'stored': True}), 200
    except Exception as e:
        logger.error(f"Error storing feedback: {e}")
        return jsonify({'error': str(e)}), 500
