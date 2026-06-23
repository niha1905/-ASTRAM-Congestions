"""
News -> Events endpoint
Scrapes recent news items and runs lightweight inference through existing predictors.
Locations are resolved via Mappls geocoding; routes use Mappls route_adv with alternatives.
"""
import logging
from datetime import datetime

from email.utils import parsedate_to_datetime
from flask import Blueprint, jsonify, request

from ..config import NEWS_MAX_ITEMS
from ..models.predictors import (
    ClosurePredictor,
    HotspotRiskPredictor,
    ImpactScorePredictor,
    ResourceDeploymentPredictor,
)
from ..news_geo import build_traffic_plan, resolve_news_location
from ..scrapers.news_scraper import fetch_google_news_rss

logger = logging.getLogger(__name__)

POSITIVE_WORDS = set(['clear', 'reopen', 'relief', 'rescued', 'safe', 'resolved', 'managed', 'minor', 'help'])
NEGATIVE_WORDS = set(['injury', 'fatal', 'dead', 'damage', 'accident', 'collision', 'riot', 'protest', 'fire', 'stampede', 'closure', 'blocked'])

news_bp = Blueprint('news', __name__, url_prefix='/api/news')


def infer_event_type(title):
    t = title.lower()
    if any(k in t for k in ['concert', 'match', 'festival', 'celebration', 'marathon', 'parade', 'conference', 'exhibition', 'fair', 'ceremony', 'procession', 'march', 'event', 'program', 'function', 'gathering', 'meeting', 'sports', 'tournament', 'vip', 'motorcade', 'state visit', 'scheduled', 'announced']):
        return 'planned'
    if any(k in t for k in ['protest', 'fire', 'accident', 'collision', 'stampede', 'riot', 'evacuation', 'collapse', 'sinkhole', 'flood']):
        return 'unplanned'
    return 'unplanned'


def parse_published(published):
    if not published:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(published)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.utcnow()


@news_bp.route('/events', methods=['GET'])
def news_events():
    """Returns recent news items with Mappls-geocoded positions and alternate routes."""
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

        tkn = title.lower() + ' ' + (it.get('summary') or '')
        pos = sum(1 for w in POSITIVE_WORDS if w in tkn)
        neg = sum(1 for w in NEGATIVE_WORDS if w in tkn)
        if pos > neg:
            sentiment = 'positive'
        elif neg > pos:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        lat, lon, zone, matched_key = resolve_news_location(
            title,
            it.get('summary', ''),
            scraper_location=it.get('location'),
        )
        found_pos = (lat, lon)

        traffic_plan = build_traffic_plan(matched_key, found_pos, zone)
        corridor = traffic_plan.get('affected', 'Unknown')

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
            'location': it.get('location'),
        }

        closure = ClosurePredictor.predict(event_type=event_type, zone=zone, corridor=corridor, priority=priority, hour=hour, duration_min=30)
        closure_prob = closure.get('closure_probability', 0) if isinstance(closure, dict) else 0

        impact = ImpactScorePredictor.predict(event_cause=event_type, corridor=corridor, priority=priority, hour=hour, weekday=weekday, closure_probability=closure_prob)
        resources = ResourceDeploymentPredictor.predict(event_type=event_type, priority=priority, zone=zone, corridor=corridor, hour=hour, closure_prob=closure_prob)

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
                'matched_location': matched_key,
            },
            'predictions': {
                'closure': closure,
                'impact': impact,
                'resources': resources,
            },
            'sentiment': sentiment,
            'position': {'lat': lat, 'lon': lon},
            'pre_measures': recs,
            'traffic_plan': traffic_plan,
        })

    return jsonify({'count': len(results), 'items': results}), 200
