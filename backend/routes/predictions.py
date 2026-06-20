"""
Prediction Routes
Handles all model prediction requests
"""

from flask import Blueprint, request, jsonify
from ..models.predictors import (
    IncidentVolumePredictor,
    ClosurePredictor,
    ResourceDeploymentPredictor,
    HotspotRiskPredictor,
    ScenarioEnginePredictor,
    DurationPredictor,
    ImpactScorePredictor,
    CascadePredictor,
    ParkingOverflowPredictor,
    GreenCorridorPredictor,
)

predictions_bp = Blueprint('predictions', __name__, url_prefix='/api/v1/predictions')


@predictions_bp.route('/incident-volume', methods=['POST'])
def predict_incident_volume():
    """
    Predict incident volume
    
    Request JSON:
    {
        "zone": "Central Zone 2",
        "corridor": "CBD 2",
        "event_type": "unplanned",
        "hour": 21,
        "weekday": 4,
        "month": 6
    }
    """
    try:
        data = request.get_json()
        
        result = IncidentVolumePredictor.predict(
            zone=data.get('zone', 'Unknown'),
            corridor=data.get('corridor', 'Unknown'),
            event_type=data.get('event_type', 'Unknown'),
            hour=int(data.get('hour', 12)),
            weekday=int(data.get('weekday', 0)),
            month=int(data.get('month', 1))
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/closure-probability', methods=['POST'])
def predict_closure():
    """
    Predict road closure probability
    
    Request JSON:
    {
        "event_type": "unplanned",
        "zone": "Central Zone 2",
        "corridor": "CBD 2",
        "priority": "High",
        "hour": 21,
        "duration_min": 45
    }
    """
    try:
        data = request.get_json()
        
        result = ClosurePredictor.predict(
            event_type=data.get('event_type', 'Unknown'),
            zone=data.get('zone', 'Unknown'),
            corridor=data.get('corridor', 'Unknown'),
            priority=data.get('priority', 'Unknown'),
            hour=int(data.get('hour', 12)),
            duration_min=int(data.get('duration_min', 30))
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/resources', methods=['POST'])
def predict_resources():
    """
    Predict required resources (officers, barricades)
    
    Request JSON:
    {
        "event_type": "unplanned",
        "priority": "High",
        "zone": "Central Zone 2",
        "corridor": "CBD 2",
        "hour": 21,
        "closure_prob": 65.5
    }
    """
    try:
        data = request.get_json()
        
        result = ResourceDeploymentPredictor.predict(
            event_type=data.get('event_type', 'Unknown'),
            priority=data.get('priority', 'Unknown'),
            zone=data.get('zone', 'Unknown'),
            corridor=data.get('corridor', 'Unknown'),
            hour=int(data.get('hour', 12)),
            closure_prob=float(data.get('closure_prob', 0))
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/hotspot-risk', methods=['POST'])
def predict_hotspot_risk():
    """
    Predict hotspot/junction risk
    
    Request JSON:
    {
        "junction": "Junction A",
        "hour": 21,
        "weekday": 4,
        "event_type": "unplanned"
    }
    """
    try:
        data = request.get_json()
        
        result = HotspotRiskPredictor.predict(
            junction=data.get('junction', 'Unknown'),
            hour=int(data.get('hour', 12)),
            weekday=int(data.get('weekday', 0)),
            event_type=data.get('event_type', 'Unknown')
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/scenario', methods=['POST'])
def predict_scenario():
    """
    Predict scenario-based impact
    
    Request JSON:
    {
        "base_scenario": "normal_traffic",
        "perturbation": "rain"
    }
    """
    try:
        data = request.get_json()
        
        result = ScenarioEnginePredictor.predict(
            base_scenario=data.get('base_scenario', 'normal'),
            perturbation=data.get('perturbation', 'rain')
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/duration', methods=['POST'])
def predict_duration():
    """Predict incident duration in minutes."""
    try:
        data = request.get_json()

        result = DurationPredictor.predict(
            event_cause=data.get('event_cause', data.get('event_type', 'Unknown')),
            veh_type=data.get('veh_type', data.get('vehicle_type', 'Unknown')),
            corridor=data.get('corridor', 'Unknown'),
            hour=int(data.get('hour', 12)),
            priority=data.get('priority', 'Unknown')
        )

        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/impact-score', methods=['POST'])
def predict_impact_score():
    """Predict composite event impact score."""
    try:
        data = request.get_json()

        result = ImpactScorePredictor.predict(
            event_cause=data.get('event_cause', data.get('event_type', 'Unknown')),
            corridor=data.get('corridor', 'Unknown'),
            priority=data.get('priority', 'Unknown'),
            hour=int(data.get('hour', 12)),
            weekday=int(data.get('weekday', 0)),
            closure_probability=float(data.get('closure_probability', data.get('closure_prob', 0)))
        )

        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/cascade', methods=['POST'])
def predict_cascade():
    """Predict congestion cascade risk."""
    try:
        data = request.get_json()

        result = CascadePredictor.predict(
            corridor=data.get('corridor', 'Unknown'),
            event_cause=data.get('event_cause', data.get('event_type', 'Unknown')),
            hour=int(data.get('hour', 12))
        )

        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/parking-overflow', methods=['POST'])
def predict_parking_overflow():
    """Predict parking overflow probability."""
    try:
        data = request.get_json()

        result = ParkingOverflowPredictor.predict(
            event_cause=data.get('event_cause', data.get('event_type', 'Unknown')),
            corridor=data.get('corridor', 'Unknown'),
            hour=int(data.get('hour', 12)),
            weekday=int(data.get('weekday', 0)),
            closure_probability=float(data.get('closure_probability', data.get('closure_prob', 0)))
        )

        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/green-corridor', methods=['POST'])
def predict_green_corridor():
    """Find a green corridor emergency path."""
    try:
        data = request.get_json()

        result = GreenCorridorPredictor.predict(
            origin_corridor=data.get('origin_corridor', data.get('source', 'Unknown')),
            destination_corridor=data.get('destination_corridor', data.get('destination', 'Unknown'))
        )

        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@predictions_bp.route('/batch', methods=['POST'])
def batch_predict():
    """
    Batch prediction for multiple requests
    
    Request JSON:
    {
        "requests": [
            {
                "type": "incident_volume",
                "params": {...}
            },
            {
                "type": "closure_probability",
                "params": {...}
            }
        ]
    }
    """
    try:
        data = request.get_json()
        requests = data.get('requests', [])
        
        results = []
        for req in requests:
            req_type = req.get('type')
            params = req.get('params', {})
            
            if req_type == 'incident_volume':
                result = IncidentVolumePredictor.predict(**params)
            elif req_type == 'closure_probability':
                result = ClosurePredictor.predict(**params)
            elif req_type == 'resources':
                result = ResourceDeploymentPredictor.predict(**params)
            elif req_type == 'hotspot_risk':
                result = HotspotRiskPredictor.predict(**params)
            elif req_type == 'scenario':
                result = ScenarioEnginePredictor.predict(**params)
            elif req_type == 'duration':
                result = DurationPredictor.predict(**params)
            elif req_type == 'impact_score':
                result = ImpactScorePredictor.predict(**params)
            elif req_type == 'cascade':
                result = CascadePredictor.predict(**params)
            elif req_type == 'parking_overflow':
                result = ParkingOverflowPredictor.predict(**params)
            elif req_type == 'green_corridor':
                result = GreenCorridorPredictor.predict(**params)
            else:
                result = {'error': f'Unknown request type: {req_type}'}
            
            results.append(result)
        
        return jsonify({'results': results, 'count': len(results)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
