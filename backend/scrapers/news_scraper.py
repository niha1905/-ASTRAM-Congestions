"""
bangalore_events_feed.py
─────────────────────────────────────────────────────────────────
Drop-in replacement for the original RSS scraper.
Returns the same List[Dict] shape the frontend already consumes,
extended with: location, severity, deployment.

Output schema per event
───────────────────────
{
    "title"      : str,          # headline / description
    "link"       : str,          # source URL
    "published"  : str,          # ISO-8601 UTC
    "summary"    : str,          # one-line human-readable summary
    "location"   : str | None,   # road / area name ("Silk Board Junction")
    "severity"   : "low" | "medium" | "high",
    "deployment" : str,          # action for traffic police
    "category"   : "planned" | "unplanned",
    "type"       : str,          # accident | flood | vip_movement | …
    "source"     : str,          # which feed this came from
}

Usage
─────
    from bangalore_events_feed import fetch_events, fetch_upcoming_events

    events = fetch_events()                  # last 48 h, all types
    events = fetch_events(hours=6)           # last 6 h only
    events = fetch_events(planned_only=True)
    events = fetch_events(unplanned_only=True)

    # ★ Police officer advance-planning view — next 24 h planned events ★
    upcoming = fetch_upcoming_events()
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ASTRAM-CongestionIQ/2.0"})

# ──────────────────────────────────────────────
# Geography — location extractor
# ──────────────────────────────────────────────

_PLACES = [
    # junctions / roads (longer first so regex prefers specific match)
    "silk board junction", "hebbal flyover", "marathahalli bridge",
    "tin factory junction", "kr puram bridge", "electronic city toll",
    "domlur flyover", "richmond circle", "freedom park", "vidhana soudha",
    "kempegowda bus stand", "indiranagar 100ft road", "outer ring road",
    "old airport road", "hosur road", "mysore road", "tumkur road",
    "bannerghatta road", "sarjapur road", "bellary road",
    "national highway 44", "nh 44", "nh 75",
    # localities
    "whitefield", "koramangala", "indiranagar", "jayanagar", "hebbal",
    "yelahanka", "kr puram", "electronic city", "marathahalli", "silk board",
    "mg road", "brigade road", "cubbon park", "bannerghatta", "jp nagar",
    "rajajinagar", "malleshwaram", "yeshwanthpur", "sarjapur", "hsr layout",
    "btm layout", "bellandur", "varthur", "kengeri", "domlur", "richmond",
    "shivajinagar", "majestic", "nagawara", "hoodi", "ulsoor", "frazer town",
    "banaswadi", "rt nagar", "seshadripuram", "vidyaranyapura",
]

_LOC_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in sorted(_PLACES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

def _location(text: str) -> Optional[str]:
    # "near X" / "at X" / "on X Road" patterns first
    pat = re.search(
        r"\b(?:near|at|on|along|via)\s+([A-Z][A-Za-z0-9 \-]{3,40}(?:Road|Junction|Circle|Flyover|Bridge|Signal|Cross|Layout|Nagar)?)",
        text,
    )
    if pat:
        return pat.group(1).strip()
    m = _LOC_RE.search(text)
    return m.group(0).title() if m else None

# ──────────────────────────────────────────────
# Severity classifier
# ──────────────────────────────────────────────

_HIGH = {
    "fatal", "death", "killed", "critical", "major accident", "massive",
    "highway blocked", "nh ", "flyover", "collapse", "riot", "stampede",
    "flood", "waterlog", "vip", "pm visit", "president", "cm visit",
    "governor", "bandh", "election", "complete block",
}
_LOW = {
    "minor", "pothole", "signal fault", "utility", "one lane",
    "parking", "slow moving", "minor works", "maintenance",
}

def _severity(text: str) -> str:
    t = text.lower()
    if any(w in t for w in _HIGH):
        return "high"
    if any(w in t for w in _LOW):
        return "low"
    return "medium"

# ──────────────────────────────────────────────
# Event type classifier
# ──────────────────────────────────────────────

_TYPE_RULES = [
    ({"vip", "convoy", "motorcade", "pm visit", "cm visit", "governor", "president"}, "vip_movement",        "planned"),
    ({"bandh", "hartal", "shutdown"},                                                  "bandh",               "unplanned"),
    ({"election", "polling", "voting"},                                                "election",            "planned"),
    ({"procession", "rath yatra", "ganesh", "muharram", "visarjan"},                  "procession",          "planned"),
    ({"rally", "protest", "agitation", "demonstration", "strike"},                    "protest",             "unplanned"),
    ({"concert", "festival", "carnival", "fair", "exhibition"},                       "cultural_event",      "planned"),
    ({"marathon", "cycling", "run", "walkathon"},                                     "mass_gathering",      "planned"),
    ({"ipl", "cricket", "football", "match", "tournament", "sports"},                 "sports_event",        "planned"),
    ({"accident", "crash", "collision", "hit"},                                        "accident",            "unplanned"),
    ({"fire", "explosion", "blast", "inferno"},                                        "fire",                "unplanned"),
    ({"flood", "waterlog", "inundated", "submerged", "heavy rain"},                   "flood",               "unplanned"),
    ({"road closed", "road block", "blocked", "diversion", "diverted"},               "road_closure",        "unplanned"),
    ({"construction", "roadworks", "road work", "utility work", "digging"},           "road_works",          "planned"),
    ({"metro", "bmtc", "bus", "transit", "train", "disruption"},                      "transit_disruption",  "unplanned"),
    ({"traffic jam", "snarl", "gridlock", "congestion"},                              "congestion",          "unplanned"),
]

def _classify(text: str) -> tuple[str, str]:
    t = text.lower()
    for keywords, type_, cat in _TYPE_RULES:
        if any(k in t for k in keywords):
            return type_, cat
    return "incident", "unplanned"

# ──────────────────────────────────────────────
# Deployment recommendation
# ──────────────────────────────────────────────

_DEPLOY: dict[str, dict[str, str]] = {
    "vip_movement": {
        "high":   "Coordinate with PSO. Clear route 30 min ahead. Officers at every junction.",
        "medium": "Coordinate with PSO. Station officers at key junctions on route.",
        "low":    "Monitor route. Standby officer at main junction.",
    },
    "bandh": {
        "high":   "Deploy on all arterials. Escort emergency vehicles. High alert.",
        "medium": "Station officers at major junctions. Monitor crowd movement.",
        "low":    "Patrol key roads. Keep radio contact with control room.",
    },
    "election": {
        "high":   "Restrict convoy movement. Coordinate with election observer.",
        "medium": "Monitor polling booth areas. Manage voter crowd flow.",
        "low":    "Routine patrol near polling booths.",
    },
    "procession": {
        "high":   "Escort duty required. Block cross-traffic at each intersection.",
        "medium": "Lead escort + 2 officers at each crossing on route.",
        "low":    "Single officer escort. Monitor route.",
    },
    "protest": {
        "high":   "Deploy extra force. Maintain barricade line. Coordinate with SHO.",
        "medium": "2 officers at rally point. Ensure crowd stays on permitted route.",
        "low":    "Monitor. Radio update every 15 min.",
    },
    "cultural_event": {
        "high":   "4+ officers at venue gates. Arrange one-way traffic flow.",
        "medium": "2 officers at venue entry/exit. Monitor dispersal route.",
        "low":    "1 officer near venue. Watch for post-event congestion.",
    },
    "sports_event": {
        "high":   "Pre-position 4 officers at stadium gates. Manage crowd surge.",
        "medium": "2 officers at stadium junction. Manage post-match dispersal.",
        "low":    "Monitor stadium road. Be ready for post-event flow.",
    },
    "mass_gathering": {
        "high":   "Block parallel roads. Deploy at start/finish and checkpoints.",
        "medium": "2 officers at key route junctions. Coordinate with organiser.",
        "low":    "Monitor route. Single officer at busiest crossing.",
    },
    "accident": {
        "high":   "Rush 2 officers. Coordinate ambulance + tow truck. Open alternate route.",
        "medium": "Deploy 1 officer. Clear vehicles within 20 min. Radio update.",
        "low":    "Single officer to manage flow. Clear lane.",
    },
    "fire": {
        "high":   "Block 200m radius. Coordinate with fire services. Divert traffic.",
        "medium": "Station officer at diversion point. Keep lane clear for fire trucks.",
        "low":    "Monitor. Keep fire truck access lane clear.",
    },
    "flood": {
        "high":   "Close all underpasses. Divert at upstream junction. Deploy at alternates.",
        "medium": "Monitor underpass water level. Station officer for early closure.",
        "low":    "Watch low-lying roads. Update control room.",
    },
    "road_closure": {
        "high":   "Post diversion 500m ahead. Station officer at diversion point.",
        "medium": "Diversion board at junction. Officer to guide traffic.",
        "low":    "Diversion sign. Check every 30 min.",
    },
    "road_works": {
        "high":   "Lane control officer. Coordinate with BBMP/contractor for schedule.",
        "medium": "Post advance warning board 300m ahead. Officer at narrowing.",
        "low":    "Ensure contractor boards are in place.",
    },
    "transit_disruption": {
        "high":   "Coordinate with BMTC/Metro control. Manage crowd at stops.",
        "medium": "Officer at main bus stop/metro station. Manage overflow.",
        "low":    "Monitor bus stop crowd. Radio control room.",
    },
    "congestion": {
        "high":   "Deploy at bottleneck junction. Manual signal control.",
        "medium": "Officer at junction. Stagger signal timing.",
        "low":    "Monitor. Intervene if queue exceeds 500m.",
    },
    "incident": {
        "high":   "Respond immediately. Assess and radio control room.",
        "medium": "Station officer. Monitor and update.",
        "low":    "Monitor situation.",
    },
}

def _deployment(type_: str, severity: str) -> str:
    return _DEPLOY.get(type_, _DEPLOY["incident"]).get(severity, "Monitor situation.")

# ──────────────────────────────────────────────
# RSS queries — planned events FIRST for police
# advance-planning priority, then unplanned
# ──────────────────────────────────────────────

_QUERIES = [
    # ── PLANNED (listed first — highest priority for advance planning) ──
    '"Bengaluru" OR "Bangalore" VIP visit OR motorcade OR "CM visit" OR "PM visit" traffic',
    '"Bengaluru" OR "Bangalore" bandh OR hartal shutdown traffic today',
    '"Bengaluru" OR "Bangalore" procession OR rath yatra OR visarjan route traffic',
    '"Bengaluru" OR "Bangalore" (protest OR rally OR strike) road block today',
    '"Bengaluru" OR "Bangalore" (concert OR festival OR fair OR carnival) traffic crowd',
    '"Bengaluru" OR "Bangalore" (IPL OR cricket OR football match) traffic today',
    '"Bengaluru" OR "Bangalore" (marathon OR walkathon OR cycling) route today',
    # ── UNPLANNED ──
    '"Bangalore" OR "Bengaluru" road accident today',
    '"Bangalore" OR "Bengaluru" fire explosion road blocked today',
    '"Bangalore" OR "Bengaluru" (waterlogging OR flooding OR flooded) road today',
    '"Bangalore" OR "Bengaluru" road closed OR blocked OR diversion today',
    '"Bangalore" OR "Bengaluru" BMTC OR metro disruption delay today',
    '"Bangalore" OR "Bengaluru" traffic jam OR snarl OR gridlock today',
]

# Title must contain at least one of these — prevents off-topic results
_MUST = {
    "traffic", "road", "block", "divert", "close", "accident", "crash",
    "flood", "water", "protest", "march", "rally", "concert", "match",
    "vip", "bandh", "fire", "jam", "signal", "junction", "metro", "bus",
    "route", "delay", "snarl", "gridlock", "procession", "flyover",
    "collision", "stampede", "riot", "strike", "explosion", "festival",
}

def _uid(title: str) -> str:
    return hashlib.md5(title.lower().strip().encode()).hexdigest()

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None

def _fetch_rss(query: str, cutoff: datetime) -> List[Dict]:
    url = GNEWS.format(q=quote_plus(query))
    try:
        r = SESSION.get(url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return []

    results = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link")  or "").strip()
        pub   = _parse_dt(item.findtext("pubDate"))

        if not title or (pub and pub < cutoff):
            continue

        tl = title.lower()
        if not any(w in tl for w in ("bangalore", "bengaluru", "blr")):
            continue
        if not any(w in tl for w in _MUST):
            continue

        results.append((title, link, pub))
    return results

# ──────────────────────────────────────────────
# Public API — matches original scraper shape
# ──────────────────────────────────────────────

def fetch_events(
    hours:           int  = 48,   # ★ widened from 24→48 so events published
                                  #   yesterday about *today* are included
    max_items:       int  = 50,
    planned_only:    bool = False,
    unplanned_only:  bool = False,
) -> List[Dict]:
    """
    Fetch Bangalore traffic-impacting events.

    Returns List[Dict] — same shape as original scraper, with extra fields:
        location, severity, deployment, category, type, source.

    Parameters
    ----------
    hours          : Only return events from the last N hours (default 48).
                     Set to 48 so that events published yesterday that
                     describe something happening today are not dropped.
    max_items      : Maximum events to return.
    planned_only   : Return only planned events.
    unplanned_only : Return only unplanned incidents.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen:    set[str]  = set()
    results: List[Dict] = []

    for query in _QUERIES:
        for title, link, pub in _fetch_rss(query, cutoff):
            uid = _uid(title)
            if uid in seen:
                continue
            seen.add(uid)

            type_, cat = _classify(title)
            loc        = _location(title)
            sev        = _severity(title)
            dep        = _deployment(type_, sev)

            # Category filter
            if planned_only   and cat != "planned":
                continue
            if unplanned_only and cat != "unplanned":
                continue

            results.append({
                # ── original fields (frontend already uses these) ──
                "title":      title,
                "link":       link,
                "published":  pub.isoformat() if pub else None,
                "summary":    f"[{type_.replace('_',' ').title()}] {loc or 'Bangalore'} — {sev.upper()} severity",
                # ── new fields for police UI ──
                "location":   loc,
                "severity":   sev,
                "deployment": dep,
                "category":   cat,
                "type":       type_,
                "source":     "Google News",
            })

            if len(results) >= max_items:
                return _ranked(results)

    return _ranked(results)


def fetch_upcoming_events(max_items: int = 50) -> List[Dict]:
    """
    ★ Police officer advance-planning view ★

    Returns ALL event types (planned + unplanned) published in the last 48 h,
    sorted soonest-published first so the officer sees what is coming up
    in the next 24 hours at the top of the list.

    High-severity events are always promoted to the top within each time slot.

    Usage
    -----
        from bangalore_events_feed import fetch_upcoming_events
        upcoming = fetch_upcoming_events()
    """
    events = fetch_events(hours=48, max_items=max_items)

    # Sort: severity HIGH → MEDIUM → LOW, then by published time ascending
    # (earliest = soonest upcoming = shown first)
    _S = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        events,
        key=lambda x: (
            _S.get(x["severity"], 1),
            x["published"] or "",   # ascending: soonest first
        ),
    )


def _ranked(items: List[Dict]) -> List[Dict]:
    """Sort: high severity first, then newest."""
    _S = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        items,
        key=lambda x: (_S.get(x["severity"], 1), x["published"] or ""),
        reverse=False,
    )


# ──────────────────────────────────────────────
# Backwards-compatible wrapper
# (drop-in for original fetch_google_news_rss)
# ──────────────────────────────────────────────

def fetch_google_news_rss(
    query:     str = "bangalore event traffic",
    max_items: int = 10,
) -> List[Dict]:
    """
    Backwards-compatible wrapper.
    Ignores `query` (we use targeted queries internally)
    and maps to fetch_events().
    """
    return fetch_events(hours=168, max_items=max_items)  # 168h = 7 days (original used 7 days)