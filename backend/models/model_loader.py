"""
Model Loader Service
Loads and manages all trained ML models with caching.
Uses joblib for serialization with graceful fallbacks for missing/corrupted models.
"""

import sys
import types
import numpy as np

import pickle
import json
import logging
import joblib
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)


def ensure_numpy_pickle_compat():
    """Alias NumPy 2.x pickle module paths when running on NumPy 1.x."""
    try:
        import numpy._core  # type: ignore  # noqa: F401
        return
    except ImportError:
        pass

    numpy_core = types.ModuleType("numpy._core")
    numpy_core.__dict__.update(np.core.__dict__)
    sys.modules.setdefault("numpy._core", numpy_core)
    sys.modules.setdefault("numpy._core.multiarray", np.core.multiarray)
    sys.modules.setdefault("numpy._core.numeric", np.core.numeric)


class ModelLoader:
    """Singleton class to load and cache trained models"""
    
    _instance = None
    _models = {}
    _encoders = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.models_dir = None
        self.loaded = False
        self.label_encoders = {}
        self.model_summary = {}
    
    def initialize(self, models_dir: Path):
        """Initialize the model loader with models directory"""
        self.models_dir = Path(models_dir)
        if not self.models_dir.exists():
            raise FileNotFoundError(f"Models directory not found: {self.models_dir}")
        
        self.load_all_models()
    
    def load_all_models(self):
        """Load all available models"""
        try:
            logger.info("Loading trained models...")
            ensure_numpy_pickle_compat()
            
            # Load label encoders first (used by prediction functions)
            self._load_label_encoders()
            
            # Load joblib-serialized models from the notebook training run
            self._load_joblib_model('incident_volume_forecaster', 'incident_volume_forecaster_lgbm.pkl')
            self._load_joblib_model('road_closure_predictor', 'road_closure_predictor_rf.pkl')
            self._load_joblib_model('officer_deployment_predictor', 'officer_deployment_gb.pkl')
            self._load_joblib_model('barricade_deployment_predictor', 'barricade_deployment_gb.pkl')
            self._load_joblib_model('hotspot_risk_predictor', 'hotspot_risk_predictor_lgbm.pkl')
            self._load_joblib_model('duration_predictor', 'incident_duration_predictor_lgbm.pkl')
            self._load_joblib_model('impact_score_model', 'event_impact_score_lgbm.pkl')
            self._load_joblib_model('cascade_predictor', 'congestion_cascade_markov.pkl')
            self._load_joblib_model('parking_overflow_predictor', 'parking_overflow_predictor.pkl')
            self._load_joblib_model('green_corridor_pathfinder', 'green_corridor_pathfinder_graph.pkl')
            
            # Load JSON scenario engine
            self._load_json_model('scenario_engine', 'scenario_perturbation_engine.json')
            self._load_model_summary()
            
            # Add fallback models for any that failed to load
            self._setup_fallback_models()
            
            self.loaded = True
            logger.info(f"Successfully loaded {len(self._models)} models")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise
    
    def _load_label_encoders(self):
        """Load label encoders for categorical variables"""
        try:
            encoder_path = self.models_dir / "advanced_label_encoders.pkl"
            if encoder_path.exists():
                self.label_encoders = joblib.load(encoder_path)
                logger.info(f"✓ Loaded label encoders for: {list(self.label_encoders.keys())}")
            else:
                logger.warning("Label encoders file not found")
        except Exception as e:
            logger.error(f"Error loading label encoders: {str(e)}")
    
    def _setup_fallback_models(self):
        """Setup fallback implementations for missing/corrupted models"""
        # Fallback for impact_score_model - uses heuristic scoring
        if 'impact_score_model' not in self._models:
            self._models['impact_score_model'] = {
                'type': 'fallback_heuristic',
                'description': 'Fallback impact score using heuristics',
                'formula': 'base_score * (1 + closure_factor + volume_factor)'
            }
            logger.warning("Using fallback implementation for impact_score_model")
        
        # Fallback for cascade_predictor - uses simple adjacency model
        if 'cascade_predictor' not in self._models:
            self._models['cascade_predictor'] = {
                'type': 'fallback_heuristic',
                'description': 'Fallback cascade probability using heuristics',
                'base_probability': 0.35
            }
            logger.warning("Using fallback implementation for cascade_predictor")
        
        # Fallback for parking_overflow_predictor
        if 'parking_overflow_predictor' not in self._models:
            self._models['parking_overflow_predictor'] = {
                'type': 'fallback_heuristic',
                'description': 'Fallback parking overflow using heuristics',
                'threshold': 0.65
            }
            logger.warning("Using fallback implementation for parking_overflow_predictor")
    
    def _load_joblib_model(self, model_name: str, filename: str):
        """Load a joblib-serialized model"""
        try:
            model_path = self.models_dir / filename
            if not model_path.exists():
                logger.warning(f"Model not found: {filename}")
                return
            
            model = joblib.load(model_path)
            if hasattr(model, 'n_jobs'):
                model.n_jobs = 1
            self._models[model_name] = model
            logger.info(f"✓ Loaded {model_name}")
        except Exception as e:
            logger.error(f"Error loading joblib model {model_name}: {str(e)}")
            # Don't raise - let fallback models handle it
            pass
    
    def _load_json_model(self, model_name: str, filename: str):
        """Load a JSON model"""
        try:
            model_path = self.models_dir / filename
            if not model_path.exists():
                logger.warning(f"Model not found: {filename}")
                return
            
            with open(model_path, 'r') as f:
                self._models[model_name] = json.load(f)
            logger.info(f"✓ Loaded {model_name}")
        except Exception as e:
            logger.error(f"Error loading JSON model {model_name}: {str(e)}")
    
    def _load_model_summary(self):
        """Load advanced model summary and metrics from JSON."""
        try:
            summary_path = self.models_dir / 'advanced_models_summary.json'
            if summary_path.exists():
                with open(summary_path, 'r', encoding='utf-8') as f:
                    self.model_summary = json.load(f)
                logger.info("✓ Loaded advanced model summary")
            else:
                logger.warning("Model summary file not found: advanced_models_summary.json")
        except Exception as e:
            logger.error(f"Error loading model summary: {str(e)}")
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model by name"""
        return self._models.get(model_name)
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get the loaded model summary metrics"""
        return self.model_summary.copy()
    
    def get_model_metrics(self, model_name: str) -> Dict[str, Any]:
        """Get metrics for a specific model"""
        return self.model_summary.get(model_name, {}).get('metrics', {})
    
    def get_all_models(self) -> Dict[str, Any]:
        """Get all loaded models"""
        return self._models.copy()
    
    def is_loaded(self) -> bool:
        """Check if models are loaded"""
        return self.loaded
    
    def get_available_models(self) -> list:
        """Get list of available models"""
        return list(self._models.keys())
    
    def encode_value(self, value: str, column: str) -> int:
        """Encode a categorical value using label encoder"""
        aliases = {
            'event_type': 'event_cause',
            'etype': 'event_cause',
            'vehicle_type': 'veh_type',
        }
        column = aliases.get(column, column)

        if column not in self.label_encoders:
            logger.warning(f"No encoder for column: {column}")
            return 0
        
        encoder = self.label_encoders[column]
        value = str(value)
        
        # Handle unseen values gracefully
        if value not in encoder.classes_:
            if "Unknown" in encoder.classes_:
                value = "Unknown"
            else:
                value = encoder.classes_[0]
        
        return int(encoder.transform([value])[0])


class EncoderManager:
    """Manages label encoders for categorical features"""
    
    _encoders = {}
    
    @classmethod
    def initialize_encoders(cls, df: pd.DataFrame):
        """Initialize encoders based on training data"""
        categorical_cols = ['event_type', 'zone', 'corridor', 'priority', 'junction']
        
        for col in categorical_cols:
            le = LabelEncoder()
            if col in df.columns:
                le.fit(df[col].astype(str))
                cls._encoders[col] = le
    
    @classmethod
    def encode_value(cls, value: str, feature: str) -> int:
        """Encode a categorical value - delegates to model_loader"""
        return model_loader.encode_value(value, feature)
    
    @classmethod
    def get_encoder(cls, feature: str) -> Optional[LabelEncoder]:
        """Get encoder for a feature"""
        return cls._encoders.get(feature)
    
    @classmethod
    def set_encoders(cls, encoders: Dict[str, LabelEncoder]):
        """Set encoders dictionary"""
        cls._encoders = encoders


# Global instances
model_loader = ModelLoader()
encoder_manager = EncoderManager()
