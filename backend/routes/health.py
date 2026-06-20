"""
Health and Status Routes
"""

from flask import Blueprint, jsonify
from ..models.model_loader import model_loader


health_bp = Blueprint('health', __name__, url_prefix='/api/health')


@health_bp.route('', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'models_loaded': model_loader.is_loaded(),
        'available_models': model_loader.get_available_models()
    })


@health_bp.route('/models', methods=['GET'])
def models_status():
    """Get status of all loaded models"""
    available = model_loader.get_available_models()
    summary = model_loader.get_model_summary()

    models = []
    for model_name in sorted(set(list(summary.keys()) + available)):
        model_info = {
            'name': model_name,
            'artifact': summary.get(model_name, {}).get('artifact'),
            'metrics': summary.get(model_name, {}).get('metrics', {}),
            'status': 'operational' if model_name in available else 'degraded'
        }
        models.append(model_info)

    return jsonify({
        'count': len(models),
        'models': models,
        'summary': summary,
        'status': 'all_loaded' if available else 'no_models_loaded'
    })
