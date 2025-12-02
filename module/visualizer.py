import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from module.openaq_api import *
from module.prediction import *

def get_aqi_color(aqi):
    if aqi <= 50:
        return '#00e400'
    elif aqi <= 100:
        return '#ffff00'
    elif aqi <= 150:
        return '#ff7e00'
    elif aqi <= 200:
        return '#ff0000'
    elif aqi <= 300:
        return '#8f3f97'
    else:
        return '#7e0023'

def get_aqi_status(aqi):
    if aqi <= 50:
        return 'Good'
    elif aqi <= 100:
        return 'Moderate'
    elif aqi <= 150:
        return 'Unhealthy for Sensitive Groups'
    elif aqi <= 200:
        return 'Unhealthy'
    elif aqi <= 300:
        return 'Very Unhealthy'
    else:
        return 'Hazardous'

def current_values(df):
    pass

def create_hourly_line_chart(hourly_df, metric='pm25'):
    df_plot = hourly_df.copy()

    # Format labels (check this afterwards)
    labels = []
    for t in df_plot['time_to']:
        # Convert to string and slice the first 19 characters
        t_str = str(t)[:19]

        # Parse the datetime
        dt = datetime.strptime(t_str, '%Y-%m-%dT%H:%M:%S')
        # or: dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ")

        # Format it
        formatted = dt.strftime('%H:%M<br>%b %d')

        labels.append(formatted)

    if metric == 'pm25':
        values = df_plot['value'].tolist()
        y_title = 'PM2.5 (μg/m³)'
        hover_template = '<b>%{x}</b><br>PM2.5: %{y:.2f} μg/m³<extra></extra>' # %{}: insert data; <extra>:remove default hover text
        colors = [get_aqi_color(aqi) for aqi in df_plot['aqi']]

    else:  # aqi
        values = df_plot['aqi'].tolist()
        y_title = 'AQI (US)'
        hover_template = '<b>%{x}</b><br>AQI: %{y}<extra></extra>'
        colors = [get_aqi_color(aqi) for aqi in values]
    
    fig = go.Figure()

    # Add bars (trace) with individual colors
    fig.add_trace(go.Bar( 
        x=labels,
        y=values,
        marker=dict( #customize the markers
            color=colors,
            line=dict(width=0) # border of marker
        ),
        hovertemplate=hover_template,
        showlegend=False
    ))

    fig.update_layout(
        title=dict(
            text='<b>Historical Data - Last 24 Hours</b>',
            x=0.5, # center
            xanchor='center',
            font=dict(size=20, color='#2d3748')
        ),
        xaxis=dict(
            title='',
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True,
            gridcolor='#e2e8f0',
            zeroline=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=400,
        margin=dict(l=60, r=40, t=60, b=40), # around the plot
        font=dict(family='Segoe UI, Arial, sans-serif', size=12, color='#2d3748')
    )

    return pio.to_html(fig, include_plotlyjs='cdn', div_id='hourly-line-chart', config={'displayModeBar': False}) # don't display mode bar

def create_prediction_column_chart(prediction_dates, prediction_values, prediction_aqi, metric='pm25'):
    if not prediction_dates or not prediction_values:
        return '<div style="text-align: center; padding: 100px; color: #718096; font-size: 16px;">⚠️ Predictions unavailable</div>'

    # Format labels
    labels = []
    for i, date in enumerate(prediction_dates):
        labels.append(f'Day {i+1}<br>{date}')

    if metric == 'pm25':
        values = prediction_values
        y_title = 'PM2.5 (μg/m³)'
        hover_template = '<b>%{x}</b><br>Predicted PM2.5: %{y:.2f} μg/m³<extra></extra'

    else:
        values = prediction_aqi
        y_title = 'AQI (US)'
        hover_template = '<b>%{x}</b><br>Predicted AQI: %{y:.2f} μg/m³<extra></extra'
    
    colors = [get_aqi_color(aqi) for aqi in prediction_aqi]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker=dict(
            color=colors,
            line=dict(width=0)
        ),
        hovertemplate=hover_template,
        showlegend=False
    ))
    
    fig.update_layout(
        title=dict(
            text='<b>7-Day Forecast</b>',
            x=0.5,
            xanchor='center',
            font=dict(size=20, color='#2d3748')
        ),
        xaxis=dict(
            title='',
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True,
            gridcolor='#e2e8f0',
            zeroline=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=400,
        margin=dict(l=60, r=40, t=60, b=40),
        font=dict(family='Segoe UI, Arial, sans-serif', size=12, color='#2d3748')
    )
    
    return pio.to_html(fig, include_plotlyjs=False, div_id='prediction-chart', config={'displayModeBar': False})

def get_aqi_status_info(aqi):
    if aqi <= 50:
        return {'status': 'Good', 'color': '#00e400', 'badge': 'badge-good'}
    elif aqi <= 100:
        return {'status': 'Moderate', 'color': '#ffff00', 'badge': 'badge-moderate'}
    elif aqi <= 150:
        return {'status': 'Unhealthy for Sensitive Groups', 'color': '#ff7e00', 'badge': 'badge-sensitive'}
    elif aqi <= 200:
        return {'status': 'Unhealthy', 'color': '#ff0000', 'badge': 'badge-unhealthy'}
    elif aqi <= 300:
        return {'status': 'Very Unhealthy', 'color': '#8f3f97', 'badge': 'badge-very-unhealthy'}
    else:
        return {'status': 'Hazardous', 'color': '#7e0023', 'badge': 'badge-hazardous'}