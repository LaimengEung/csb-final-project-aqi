import pandas as pd
import numpy as np
import joblib
import os
from datetime import timedelta

def load_artifacts(country_id):
    model_path =  f'models/aqi_model_{country_id}.pkl'
    scaler_path =  f'models/aqi_scaler_{country_id}.pkl'
    
    model = None
    scaler = None
    
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            print(f"✅ Model loaded: {model.__class__.__name__}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            
    else:
        print(f"❌ Model not found at {model_path}")
        print(f"   Available files: {os.listdir('.')}")
        
    if os.path.exists(scaler_path):
        try:
            scaler = joblib.load(scaler_path)
            print(f"✅ Scaler loaded")
        except Exception as e:
            print(f"❌ Error loading scaler: {e}")
    else:
        print(f"❌ Scaler not found at {scaler_path}")
        print(f"   Available files: {os.listdir('.')}")
        
    return model, scaler

def create_features(diff_history, next_date):
    features = {}
    
    def get_lag(data, n):
        """Get nth lag from end of data"""
        if len(data) >= n:
            return float(data[-n])
        return 0.0
    
    # 1. Lags of differences
    for lag in range(1, 8):
        features[f'lag_{lag}'] = get_lag(diff_history, lag)
    features['lag_14'] = get_lag(diff_history, 14)
    features['lag_30'] = get_lag(diff_history, 30)
    
    # 2. Rolling statistics
    recent_diffs = pd.Series(diff_history[-30:] if len(diff_history) >= 30 else diff_history)
    features['rolling_mean_7'] = float(recent_diffs.tail(7).mean()) if len(recent_diffs) >= 7 else 0.0
    features['rolling_std_7'] = float(recent_diffs.tail(7).std()) if len(recent_diffs) >= 7 else 0.0
    
    # 3. Seasonality features
    features['day_of_week_sin'] = float(np.sin(2 * np.pi * next_date.dayofweek / 7))
    features['day_of_week_cos'] = float(np.cos(2 * np.pi * next_date.dayofweek / 7))
    features['day_of_year_sin'] = float(np.sin(2 * np.pi * next_date.dayofyear / 365.25))
    features['day_of_year_cos'] = float(np.cos(2 * np.pi * next_date.dayofyear / 365.25))
    
    return features

def predict_7_days(df, country_id=None):
    """Predict next 7 days of PM2.5"""
    print(f"\n🚀 Starting prediction...")
    model, scaler = load_artifacts(country_id)
    
    if model is None or scaler is None:
        print(f"⚠️  Model or Scaler not found!")
        return [], []

    try:
        # Ensure time_to is index
        df['time_to'] = pd.to_datetime(df['time_to'])
        if 'time_to' in df.columns:
            df = df.set_index('time_to')
        
        print(f"📅 DataFrame shape: {df.shape}")
        print(f"📅 Index type: {type(df.index)}")
        
        # Resample to daily
        df_daily = df.resample('D').mean()
        df_daily['value'] = df_daily['value'].interpolate(method='linear')
        
        print(f"📅 Daily data shape: {df_daily.shape}")
        
        # Calculate differences
        df_daily['diff'] = df_daily['value'].diff()
        
        # Get history
        history_diff = df_daily['diff'].dropna().tolist()
        last_absolute_value = df_daily['value'].iloc[-1]
        current_date = df_daily.index[-1]
        
        print(f"📊 Last value: {last_absolute_value:.2f}")
        print(f"📊 History diffs available: {len(history_diff)}")
        print(f"📅 Current date: {current_date}")
        
        future_predictions = []
        future_dates = []
        
        # Feature order must match training
        feature_order = [
            'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_5', 'lag_6', 'lag_7', 
            'lag_14', 'lag_30', 
            'rolling_mean_7', 'rolling_std_7',
            'day_of_week_sin', 'day_of_week_cos', 'day_of_year_sin', 'day_of_year_cos'
        ]
        
        # Predict next 7 days
        for i in range(1, 8):
            next_date = current_date + timedelta(days=i)
            
            # Create features
            features = create_features(history_diff, next_date)
            
            X_next = pd.DataFrame([features], columns=feature_order)
            
            # Scale features
            X_next_scaled = scaler.transform(X_next)
            
            # Predict difference
            pred_diff = float(model.predict(X_next_scaled)[0])
            
            # Reconstruct absolute value
            pred_value = max(0, last_absolute_value + pred_diff)
            
            future_predictions.append(round(pred_value, 2))
            future_dates.append(next_date.strftime('%Y-%m-%d'))
            
            print(f"  Day {i}: {next_date.strftime('%Y-%m-%d')} → {pred_value:.2f} μg/m³ (Δ: {pred_diff:.2f})")
            
            # Update for next iteration
            history_diff.append(pred_diff)
            last_absolute_value = pred_value
        
        print(f"✅ Predictions generated!")
        return future_dates, future_predictions
        
    except Exception as e:
        print(f"❌ Error during prediction: {e}")
        import traceback
        traceback.print_exc()
        return [], []