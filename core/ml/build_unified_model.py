import joblib
import json
from pathlib import Path
import sys
import os

# Add project root to sys.path so we can import the model class properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.ml.ai_credit_score_model import AICreditScoreModel

def build_model():
    models_dir = Path(__file__).parent / "models"
    
    fraud_path = models_dir / "fraud_detection_pipeline.joblib"
    credit_path = models_dir / "credit_risk_pipeline.joblib"
    
    fraud_meta_path = models_dir / "fraud_metadata.json"
    credit_meta_path = models_dir / "credit_risk_metadata.json"
    
    fraud_payload = joblib.load(fraud_path)
    credit_payload = joblib.load(credit_path)
    
    fraud_model = fraud_payload['model'] if isinstance(fraud_payload, dict) and 'model' in fraud_payload else fraud_payload
    credit_model = credit_payload['model'] if isinstance(credit_payload, dict) and 'model' in credit_payload else credit_payload
    
    with open(fraud_meta_path, 'r') as f:
        fraud_features = json.load(f)["feature_columns"]
        
    with open(credit_meta_path, 'r') as f:
        credit_features = json.load(f)["feature_columns"]
        
    ai_model = AICreditScoreModel(fraud_model, credit_model, fraud_features, credit_features)
    
    out_path = models_dir / "AI_Credit_Score.joblib"
    joblib.dump(ai_model, out_path)
    print(f"Successfully saved {out_path}")

if __name__ == "__main__":
    build_model()
