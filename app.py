from flask import Flask, render_template, request, jsonify
from module.openaq_api import *
from module.prediction import predict_7_days
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def pm25_to_aqi(pm25):
    """Convert PM2.5 to AQI (US EPA standard)"""
    if pm25 < 0:
        return 0
    if pm25 <= 12.0:
        return round(((50 - 0) / (12.0 - 0)) * (pm25 - 0) + 0)
    if pm25 <= 35.4:
        return round(((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1) + 51)
    if pm25 <= 55.4:
        return round(((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5) + 101)
    if pm25 <= 150.4:
        return round(((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5) + 151)
    if pm25 <= 250.4:
        return round(((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5) + 201)
    if pm25 <= 350.4:
        return round(((400 - 301) / (350.4 - 250.5)) * (pm25 - 250.5) + 301)
    if pm25 <= 500.4:
        return round(((500 - 401) / (500.4 - 350.5)) * (pm25 - 350.5) + 401)
    return 500

def get_aqi_status_color(aqi):
    """Get AQI status and color class"""
    if aqi <= 50:
        return {'status': 'Good', 'class': 'aqi-good', 'badge': 'badge-good', 'color': '#10b981'}
    elif aqi <= 100:
        return {'status': 'Moderate', 'class': 'aqi-moderate', 'badge': 'badge-moderate', 'color': '#f59e0b'}
    elif aqi <= 150:
        return {'status': 'Unhealthy for Sensitive Groups', 'class': 'aqi-sensitive', 'badge': 'badge-sensitive', 'color': '#f97316'}
    elif aqi <= 200:
        return {'status': 'Unhealthy', 'class': 'aqi-unhealthy', 'badge': 'badge-unhealthy', 'color': '#ef4444'}
    elif aqi <= 300:
        return {'status': 'Very Unhealthy', 'class': 'aqi-very-unhealthy', 'badge': 'badge-very-unhealthy', 'color': '#991b1b'}
    else:
        return {'status': 'Hazardous', 'class': 'aqi-hazardous', 'badge': 'badge-hazardous', 'color': '#7c2d12'}

def create_pm25_chart(history_labels, history_values, prediction_dates, prediction_values):
    """Create interactive Plotly chart for PM2.5"""
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add historical data
    fig.add_trace(go.Scatter(
        x=history_labels,
        y=history_values,
        mode='lines+markers',
        name='Historical PM2.5',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)',
        hovertemplate='<b>%{x}</b><br>PM2.5: %{y:.2f} μg/m³<extra></extra>'
    ))
    
    # Add prediction data (with None to create gap)
    if prediction_dates and prediction_values:
        last_historical_date = history_labels[-1]
        first_prediction_date = prediction_dates[0]
        
        fig.add_trace(go.Scatter(
            x=[last_historical_date] + prediction_dates,
            y=[history_values[-1]] + prediction_values,
            mode='lines+markers',
            name='7-Day Forecast',
            line=dict(color='#f59e0b', width=3, dash='dash'),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(245, 158, 11, 0.2)',
            hovertemplate='<b>%{x}</b><br>Forecast: %{y:.2f} μg/m³<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': '<b>PM2.5 Levels - Historical & 7-Day Forecast</b>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title='Date',
        yaxis_title='PM2.5 (μg/m³)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        margin=dict(l=50, r=50, t=80, b=50),
        font=dict(family='Arial, sans-serif', size=12),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    # Add range slider
    fig.update_xaxes(rangeslider_visible=False, rangeselector=dict(
        buttons=list([
            dict(count=7, label='1w', step='day'),
            dict(count=14, label='2w', step='day'),
            dict(count=1, label='1m', step='month'),
            dict(step='all', label='All')
        ])
    ))
    
    return pio.to_html(fig, include_plotlyjs='cdn', div_id='pm25-chart')

def create_ranking_chart(ranking_data):
    """Create bar chart for top 10 stations"""
    
    if not ranking_data or len(ranking_data) == 0:
        return "<p>No ranking data available</p>"
    
    stations = [r['name'] for r in ranking_data[:10]]
    values = [float(r['value']) for r in ranking_data[:10]]
    aqi_values = [pm25_to_aqi(v) for v in values]
    
    # Color based on AQI
    colors = [get_aqi_status_color(aqi)['color'] for aqi in aqi_values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=stations,
        y=values,
        marker=dict(color=colors),
        text=[f"{v:.1f} μg/m³" for v in values],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>PM2.5: %{y:.2f} μg/m³<br>AQI: ' + 
                     [str(aqi) for aqi in aqi_values].__repr__() + '<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': '<b>Top 10 Most Polluted Stations</b>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title='Station Name',
        yaxis_title='PM2.5 (μg/m³)',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=80, b=100),
        font=dict(family='Arial, sans-serif', size=11),
        xaxis_tickangle=-45
    )
    
    return pio.to_html(fig, include_plotlyjs=False, div_id='ranking-chart')
# Add these before the @app.route decorators in app1.py

@app.template_filter('pm25_to_aqi_value')
def pm25_to_aqi_filter(value):
    return pm25_to_aqi(value)

@app.template_filter('aqi_status')
def aqi_status_filter(value):
    aqi = pm25_to_aqi(value)
    return get_aqi_status_color(aqi)['status']

@app.context_processor
def inject_utils():
    return {
        'pm25_to_aqi_value': pm25_to_aqi,
        'get_aqi_status': lambda v: get_aqi_status_color(pm25_to_aqi(v))['status']
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    country = request.args.get('country', '').strip()
    if not country:
        return render_template('index.html', error='Please enter a country name')  
    try:
        country_id = get_country_by_name(country)
        df = get_daily_data_by_country(country, country_id)

        # Calculate metrics
        latest_value = round(df['value'].iloc[-1], 2)
        latest_aqi = pm25_to_aqi(latest_value)
        avg_pm25 = round(df['value'].mean(), 2)
        avg_aqi = pm25_to_aqi(avg_pm25)

        # History Data
        history_labels = [str(date)[:10] for date in df['time_to']]
        history_values = df['value'].round(2).tolist()

        # ✅ Get 7-day predictions
        print(f"📊 Starting predictions for {country}...")
        prediction_dates, prediction_values = predict_7_days(df, country_id)
        
        print(f"📅 Prediction dates: {prediction_dates}")
        print(f"📈 Prediction values: {prediction_values}")
        
        # ✅ Get ranking data
        ranking_df = get_ranking_by_country(country_id)
        ranking_data = ranking_df.to_dict('records') if ranking_df is not None else []
        
        # ✅ Generate Plotly charts
        pm25_chart_html = create_pm25_chart(history_labels, history_values, prediction_dates, prediction_values)
        ranking_chart_html = create_ranking_chart(ranking_data)
        
        # Get AQI color info
        aqi_info = get_aqi_status_color(latest_aqi)
        
        return render_template('dashboard.html',
                       country=country,
                       current_pm25=latest_value,
                       current_aqi=int(latest_aqi),
                       aqi_status=aqi_info['status'],
                       aqi_color=aqi_info['color'],
                       avg_pm25=avg_pm25,
                       avg_aqi=int(avg_aqi),
                       pm25_chart=pm25_chart_html,
                       ranking_chart=ranking_chart_html,
                       ranking_data=ranking_data,
                       now=datetime.now()
                       )
    
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return render_template('index.html', error=f'Error processing data: {str(e)}')

@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    country = request.args.get('country')
    if not country:
        return jsonify({'error': 'Country not provided'}), 400
    
    try:
        country_id = get_country_by_name(country)
        ranking_df = get_ranking_by_country(country_id)
        return jsonify(ranking_df.to_dict('records'))
    except Exception as e:
        print(f"❌ Ranking API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def api_predict():
    """API endpoint to get predictions"""
    try:
        data = request.json
        country = data.get('country')
        
        if not country:
            return jsonify({'error': 'Country not provided'}), 400
        
        country_id = get_country_by_name(country)
        df = get_daily_data_by_country(country, country_id)
        
        prediction_dates, prediction_values = predict_7_days(df, country_id)
        
        if not prediction_dates or not prediction_values:
            return jsonify({'error': 'No predictions available'}), 500
        
        return jsonify({
            'dates': prediction_dates,
            'values': prediction_values
        })
    except Exception as e:
        print(f"❌ Prediction API error: {e}")
        return jsonify({'error': str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)