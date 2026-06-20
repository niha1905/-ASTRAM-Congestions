"""
Flask Application Factory
"""

import logging
import os
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from .config import config
from .models.model_loader import model_loader
from .routes.health import health_bp
from .routes.predictions import predictions_bp
from .routes.dashboard import dashboard_bp
from .routes.news import news_bp

# Load environment variables
load_dotenv()


def create_app(config_name: str = None) -> Flask:
    """Application factory"""
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    cfg = config.get(config_name, config['default'])
    
    # Create app
    app = Flask(__name__)
    # Avoid automatic redirects for requests with/without trailing slash (fixes CORS preflight redirects)
    app.url_map.strict_slashes = False
    app.config.from_object(cfg)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Setup CORS
    CORS(app, origins=cfg.CORS_ORIGINS)
    
    # Initialize models
    try:
        model_loader.initialize(cfg.MODELS_DIR)
        logger.info("✓ Models initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize models: {str(e)}")
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(news_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'service': 'Traffic Congestion ML API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/api/health',
                'health_models': '/api/health/models',
                'predictions': '/api/v1/predictions'
                , 'news_events': '/api/news/events'
            }
        })
    
    logger.info("✓ Flask app initialized")
    return app
