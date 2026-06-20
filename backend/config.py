import os

# Mappls REST API key – should be set in environment variables.
MAPPLS_REST_API_KEY = os.getenv('MAPPLS_REST_API_KEY', '')

# ── News scraping config ──────────────────────────────────────────────────────
# Max news items to fetch per dashboard refresh (override via env).
NEWS_MAX_ITEMS: int = int(os.getenv('NEWS_MAX_ITEMS', '20'))
# Default RSS search query.
NEWS_QUERY: str = os.getenv('NEWS_QUERY', 'bangalore event traffic')

# ── Time-series config ────────────────────────────────────────────────────────
# Hour at which the 12-point forecast series begins (0-23).
SERIES_START_HOUR: int = int(os.getenv('SERIES_START_HOUR', '6'))
# Number of hourly points in the series.
SERIES_WINDOW_HOURS: int = int(os.getenv('SERIES_WINDOW_HOURS', '12'))

# ── Bangalore locality coordinates ────────────────────────────────────────────
# ── Bangalore locality / junction coordinates ────────────────────────────────
# Covers every place name the news scraper (_PLACES list) can extract.
# Coordinates are at the actual junction / road midpoint, not suburb centroids.
# Add more entries as new locations appear in headlines.
BANGALORE_LOCATIONS: dict = {
    # ── Major junctions & flyovers (most specific — matched first) ──
    'silk board junction':      (12.9175, 77.6229),
    'hebbal flyover':           (13.0358, 77.5966),
    'marathahalli bridge':      (12.9591, 77.7008),
    'tin factory junction':     (12.9985, 77.6608),
    'kr puram bridge':          (13.0002, 77.6952),
    'electronic city toll':     (12.8390, 77.6700),
    'domlur flyover':           (12.9601, 77.6466),
    'richmond circle':          (12.9630, 77.5985),
    'freedom park':             (12.9785, 77.5736),
    'vidhana soudha':           (12.9793, 77.5906),
    'kempegowda bus stand':     (12.9767, 77.5713),
    # ── Major roads ──
    'indiranagar 100ft road':   (12.9719, 77.6412),
    'outer ring road':          (12.9250, 77.6833),
    'old airport road':         (12.9600, 77.6484),
    'hosur road':               (12.9175, 77.6229),
    'mysore road':              (12.9439, 77.5282),
    'tumkur road':              (13.0319, 77.5383),
    'bannerghatta road':        (12.8884, 77.5974),
    'sarjapur road':            (12.9100, 77.6869),
    'bellary road':             (13.0470, 77.5850),
    'national highway 44':      (12.9175, 77.6229),
    'nh 44':                    (12.9175, 77.6229),
    'nh 75':                    (12.9439, 77.5282),
    # ── Localities / areas ──
    'silk board':               (12.9175, 77.6229),
    'whitefield':               (12.9699, 77.7490),
    'koramangala':              (12.9352, 77.6245),
    'indiranagar':              (12.9719, 77.6412),
    'jayanagar':                (12.9372, 77.5956),
    'hebbal':                   (13.0358, 77.5966),
    'yelahanka':                (13.0845, 77.5938),
    'kr puram':                 (13.0002, 77.6952),
    'electronic city':          (12.8498, 77.6624),
    'marathahalli':             (12.9591, 77.7008),
    'mg road':                  (12.9754, 77.6050),
    'brigade road':             (12.9716, 77.6074),
    'cubbon park':              (12.9763, 77.5929),
    'bannerghatta':             (12.8884, 77.5974),
    'jp nagar':                 (12.9082, 77.5859),
    'rajajinagar':              (12.9979, 77.5546),
    'malleshwaram':             (13.0027, 77.5700),
    'yeshwanthpur':             (13.0215, 77.5483),
    'sarjapur':                 (12.8590, 77.7030),
    'hsr layout':               (12.9116, 77.6474),
    'btm layout':               (12.9165, 77.6101),
    'bellandur':                (12.9254, 77.6749),
    'varthur':                  (12.9375, 77.7473),
    'kengeri':                  (12.9076, 77.4826),
    'domlur':                   (12.9601, 77.6466),
    'richmond':                 (12.9630, 77.5985),
    'shivajinagar':             (12.9860, 77.6011),
    'majestic':                 (12.9767, 77.5713),
    'nagawara':                 (13.0449, 77.6220),
    'hoodi':                    (12.9857, 77.7000),
    'ulsoor':                   (12.9808, 77.6188),
    'frazer town':              (12.9898, 77.6161),
    'banaswadi':                (13.0143, 77.6490),
    'rt nagar':                 (13.0204, 77.5935),
    'seshadripuram':            (13.0018, 77.5726),
    'vidyaranyapura':           (13.0624, 77.5590),
}

# ── Corridor base congestion ──────────────────────────────────────────────────
# Baseline congestion % for known corridors used when no live data is available.
# These are reference values from historical averages; adjust as data improves.
CORRIDOR_BASE_CONGESTION: dict = {
    'Hosur Road':  int(os.getenv('BASE_CONGESTION_HOSUR', '68')),
    'ORR East 1':  int(os.getenv('BASE_CONGESTION_ORR_E1', '75')),
    'CBD 2':       int(os.getenv('BASE_CONGESTION_CBD2', '45')),
    'CBD 1':       int(os.getenv('BASE_CONGESTION_CBD1', '82')),
}

from pathlib import Path

class Config:
    DEBUG = False
    TESTING = False
    MODELS_DIR = Path(__file__).resolve().parent.parent / 'trained_models'
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001').split(',')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    pass

class TestingConfig(Config):
    TESTING = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
