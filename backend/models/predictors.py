"""
Prediction Services for ML Models
Implements prediction functions for each model
"""

import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from .model_loader import model_loader, encoder_manager
from .notebook_predictors import (
    apply_scenario,
    green_corridor_path,
    predict_cascade_probability,
    predict_duration_minutes,
    predict_impact_score,
    predict_parking_overflow,
)

logger = logging.getLogger(__name__)


class IncidentVolumePredictor:
    """Predicts incident volume for given parameters"""
    
    @staticmethod
    def predict(zone: str, corridor: str, event_type: str, hour: int, 
                weekday: int, month: int) -> Dict[str, Any]:
        """
        Predict incident volume
        
        Args:
            zone: Zone name
            corridor: Corridor name
            event_type: Type of event ('planned' or 'unplanned')
            hour: Hour of day (0-23)
            weekday: Day of week (0-6)
            month: Month (1-12)
        
        Returns:
            Dictionary with prediction and confidence
        """
        try:
            model = model_loader.get_model('incident_volume_forecaster')
            if model is None:
                return {'error': 'Model not loaded', 'prediction': 0}
            
            row = pd.DataFrame([{
                'zone_enc': encoder_manager.encode_value(zone, 'zone'),
                'corridor_enc': encoder_manager.encode_value(corridor, 'corridor'),
                'etype_enc': encoder_manager.encode_value(event_type, 'event_type'),
                'hour': hour,
                'weekday': weekday,
                'month': month,
            }])
            
            prediction = max(0, round(float(model.predict(row)[0])))
            
            return {
                'success': True,
                'prediction': prediction,
                'unit': 'incidents',
                'parameters': {'zone': zone, 'corridor': corridor, 'event_type': event_type}
            }
        except Exception as e:
            logger.error(f"Error in incident volume prediction: {str(e)}")
            return {'error': str(e), 'prediction': 0}


class ClosurePredictor:
    """Predicts probability of road closure"""
    
    @staticmethod
    def predict(event_type: str, zone: str, corridor: str, priority: str, 
                hour: int, duration_min: int) -> Dict[str, Any]:
        """
        Predict closure probability
        
        Args:
            event_type: Type of event
            zone: Zone name
            corridor: Corridor name
            priority: Priority level ('High', 'Low', etc.)
            hour: Hour of day
            duration_min: Expected duration in minutes
        
        Returns:
            Dictionary with closure probability (0-100)
        """
        try:
            model = model_loader.get_model('road_closure_predictor')
            if model is None:
                return {'error': 'Model not loaded', 'prediction': 0}
            
            row = pd.DataFrame([{
                'event_type_enc': encoder_manager.encode_value(event_type, 'event_type'),
                'zone_enc': encoder_manager.encode_value(zone, 'zone'),
                'corridor_enc': encoder_manager.encode_value(corridor, 'corridor'),
                'priority_enc': encoder_manager.encode_value(priority, 'priority'),
                'hour': hour,
                'duration_min': duration_min,
            }])
            
            features = getattr(model, 'feature_names_in_', row.columns)
            x = row[list(features)] if len(features) else row
            closure_prob = round(float(model.predict_proba(x)[0, 1]) * 100, 1) if hasattr(model, 'predict_proba') else 0
            
            return {
                'success': True,
                'closure_probability': closure_prob,
                'will_close': closure_prob >= 50,
                'risk_level': 'high' if closure_prob >= 70 else 'medium' if closure_prob >= 50 else 'low'
            }
        except Exception as e:
            logger.error(f"Error in closure prediction: {str(e)}")
            return {'error': str(e), 'prediction': 0}


class ResourceDeploymentPredictor:
    """Predicts required officers and barricades"""
    
    @staticmethod
    def predict(event_type: str, priority: str, zone: str, corridor: str, 
                hour: int, closure_prob: float = 0) -> Dict[str, Any]:
        """
        Predict resource deployment needs
        
        Args:
            event_type: Type of event
            priority: Priority level
            zone: Zone name
            corridor: Corridor name
            hour: Hour of day
            closure_prob: Probability of closure (0-100)
        
        Returns:
            Dictionary with officers and barricades needed
        """
        try:
            officer_model = model_loader.get_model('officer_deployment_predictor')
            barricade_model = model_loader.get_model('barricade_deployment_predictor')
            row = pd.DataFrame([{
                'event_type_enc': encoder_manager.encode_value(event_type, 'event_type'),
                'priority_enc': encoder_manager.encode_value(priority, 'priority'),
                'zone_enc': encoder_manager.encode_value(zone, 'zone'),
                'corridor_enc': encoder_manager.encode_value(corridor, 'corridor'),
                'hour': hour,
            }])
            
            if officer_model is not None:
                officers = max(1, round(float(officer_model.predict(row)[0])))
                officer_source = 'model'
            else:
                officers = max(1, int(round(2 + closure_prob / 15 + (2 if priority.lower() == 'high' else 0))))
                officer_source = 'fallback'

            if barricade_model is not None:
                barricades = max(0, round(float(barricade_model.predict(row)[0])))
                barricade_source = 'model'
            else:
                barricades = max(0, int(round(closure_prob / 20 + (2 if priority.lower() == 'high' else 0))))
                barricade_source = 'fallback'
            
            return {
                'success': True,
                'officers_needed': officers,
                'barricades_needed': barricades,
                'total_resources': officers + barricades,
                'sources': {
                    'officers': officer_source,
                    'barricades': barricade_source
                }
            }
        except Exception as e:
            logger.error(f"Error in resource deployment prediction: {str(e)}")
            return {'error': str(e), 'officers': 0, 'barricades': 0}


class HotspotRiskPredictor:
    """Predicts risk scores for junctions"""
    
    @staticmethod
    def predict(junction: str, hour: int, weekday: int, event_type: str) -> Dict[str, Any]:
        """
        Predict hotspot risk score
        
        Args:
            junction: Junction name
            hour: Hour of day
            weekday: Day of week
            event_type: Type of event
        
        Returns:
            Dictionary with risk score (0-100)
        """
        try:
            model = model_loader.get_model('hotspot_risk_predictor')
            if model is None:
                return {'error': 'Model not loaded', 'risk_score': 0}
            
            row = pd.DataFrame([{
                'junction_enc': encoder_manager.encode_value(junction, 'junction'),
                'hour': hour,
                'weekday': weekday,
                'etype_enc': encoder_manager.encode_value(event_type, 'event_type'),
            }])
            
            risk_score = max(0, min(100, float(model.predict(row)[0])))
            
            return {
                'success': True,
                'risk_score': round(risk_score, 2),
                'risk_level': 'critical' if risk_score >= 80 else 'high' if risk_score >= 60 else 'medium' if risk_score >= 40 else 'low',
                'junction': junction
            }
        except Exception as e:
            logger.error(f"Error in hotspot risk prediction: {str(e)}")
            return {'error': str(e), 'risk_score': 0}


class ScenarioEnginePredictor:
    """Handles scenario-based perturbation predictions"""
    
    @staticmethod
    def predict(base_scenario: str, perturbation: str) -> Dict[str, Any]:
        """
        Predict scenario impact
        
        Args:
            base_scenario: Base scenario name
            perturbation: Perturbation type ('rain', 'metro_breakdown', etc.)
        
        Returns:
            Dictionary with scenario impact metrics
        """
        try:
            model = model_loader.get_model('scenario_engine')
            if model is None:
                return {'error': 'Model not loaded', 'impact': {}}
            
            scenarios = model.get('scenarios', model) if isinstance(model, dict) else {}
            if isinstance(scenarios, dict) and perturbation in scenarios:
                impact = scenarios[perturbation]
                return {
                    'success': True,
                    'perturbation': perturbation,
                    'impact': impact,
                    'duration_multiplier': impact.get('duration_multiplier', 1.0)
                }
            else:
                return {'error': f'Perturbation {perturbation} not found in model'}
        except Exception as e:
            logger.error(f"Error in scenario prediction: {str(e)}")
            return {'error': str(e)}


class DurationPredictor:
    """Predicts incident duration using the notebook duration model"""

    @staticmethod
    def predict(event_cause: str, veh_type: str, corridor: str, hour: int, priority: str) -> Dict[str, Any]:
        try:
            duration = predict_duration_minutes(event_cause, veh_type, corridor, hour, priority)
            return {
                'success': True,
                'estimated_duration_min': duration,
                'unit': 'minutes'
            }
        except Exception as e:
            logger.error(f"Error in duration prediction: {str(e)}")
            return {'error': str(e), 'estimated_duration_min': 0}


class ImpactScorePredictor:
    """Predicts composite event impact score"""

    @staticmethod
    def predict(event_cause: str, corridor: str, priority: str, hour: int,
                weekday: int, closure_probability: float) -> Dict[str, Any]:
        try:
            score = predict_impact_score(event_cause, corridor, priority, hour, weekday, closure_probability)
            return {
                'success': True,
                'impact_score': score,
                'risk_level': 'critical' if score >= 80 else 'high' if score >= 60 else 'medium' if score >= 40 else 'low'
            }
        except Exception as e:
            logger.error(f"Error in impact score prediction: {str(e)}")
            return {'error': str(e), 'impact_score': 0}


class CascadePredictor:
    """Predicts congestion cascade probabilities"""

    @staticmethod
    def predict(corridor: str, event_cause: str, hour: int) -> Dict[str, Any]:
        try:
            cascade = predict_cascade_probability(corridor, event_cause, hour)
            return {'success': True, **cascade}
        except Exception as e:
            logger.error(f"Error in cascade prediction: {str(e)}")
            return {'error': str(e), 'prob_30': 0, 'prob_60': 0}


class ParkingOverflowPredictor:
    """Predicts parking overflow probability"""

    @staticmethod
    def predict(event_cause: str, corridor: str, hour: int, weekday: int,
                closure_probability: float) -> Dict[str, Any]:
        try:
            probability = predict_parking_overflow(event_cause, corridor, hour, weekday, closure_probability)
            return {
                'success': True,
                'parking_overflow_probability': probability,
                'risk_level': 'high' if probability >= 70 else 'medium' if probability >= 40 else 'low'
            }
        except Exception as e:
            logger.error(f"Error in parking overflow prediction: {str(e)}")
            return {'error': str(e), 'parking_overflow_probability': 0}


class GreenCorridorPredictor:
    """Finds emergency green-corridor path between corridors"""

    @staticmethod
    def predict(origin_corridor: str, destination_corridor: str) -> Dict[str, Any]:
        try:
            path = green_corridor_path(origin_corridor, destination_corridor)
            return {'success': True, **path}
        except Exception as e:
            logger.error(f"Error in green corridor prediction: {str(e)}")
            return {'error': str(e), 'path': []}


# Predictor factory for easy access
class PredictorFactory:
    """Factory for accessing all predictors"""
    
    predictors = {
        'incident_volume': IncidentVolumePredictor,
        'closure': ClosurePredictor,
        'resources': ResourceDeploymentPredictor,
        'hotspot_risk': HotspotRiskPredictor,
        'scenario': ScenarioEnginePredictor,
        'duration': DurationPredictor,
        'impact_score': ImpactScorePredictor,
        'cascade': CascadePredictor,
        'parking_overflow': ParkingOverflowPredictor,
        'green_corridor': GreenCorridorPredictor,
    }
    
    @classmethod
    def get_predictor(cls, name: str):
        """Get a predictor by name"""
        return cls.predictors.get(name)
