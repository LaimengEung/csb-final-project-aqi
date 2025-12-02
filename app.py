from flask import Flask, render_template, request
from module.openaq_api import *
from module.prediction import *
from module.visualizer import *
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    country = request.args.get('country', '').strip() #  key-value pairs appended to the URL after '?'
    metric = request.args.get('metric', 'pm25') # default to pm25

    if not country:
        return render_template('index.html', error='Please enter a country name')
    
    try:
        country_id = get_country_by_name(country)
        if isinstance(country_id, str): # country_id returns error
            return render_template('index.html', error=country_id)
        
        # Get hourly data
        hourly_df = get_daily_data_by_country(country, country_id)

        # Get latest info for the card
        latest_pm25 = round(hourly_df['value'].iloc[-1])
        latest_aqi = int(hourly_df['aqi'].iloc[-1])
        aqi_info = get_aqi_status_info(latest_aqi) 

        # Get 7-day predictions
        last_30_data = get_historic_data_by_country(country, country_id, days=30) # get last 30-day data for ML to have more differences and better rolling windows
        prediction_dates, prediction_values, prediction_aqi = predict_7_days(last_30_data, country_id)

        # Get top 10 stations
        ranking_df = get_ranking_by_country(country_id)
        top_10_stations = ranking_df.head(10).to_dict('records') if ranking_df is not None else []

        # Create charts by selected metric
        hourly_line_chart = create_hourly_line_chart(hourly_df, metric)
        prediction_column_chart = create_prediction_column_chart(prediction_dates, prediction_values, prediction_aqi, metric)

        return render_template('dashboard.html',
                               country=country,
                               current_pm25=latest_pm25,
                               current_aqi=latest_aqi,
                               aqi_info=aqi_info['status'],
                               aqi_color=aqi_info['color'],
                               historical_chart=hourly_line_chart,
                               prediction_chart=prediction_column_chart,
                               top_10_stations=top_10_stations,
                               selected_metric=metric,
                               now=datetime.now(),
                               get_aqi_status_info=get_aqi_status_info)
    
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback # extract, format, and print info about stack traces
        traceback.print_exc() # print exception
        return render_template('index.html', error=f'Error processing data: {e}')
    
if __name__ == "__main__":
    app.run(debug=True)