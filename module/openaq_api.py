from openaq import OpenAQ
from datetime import datetime, timedelta
import aqi
import pandas as pd
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENAQ_API_KEY')
client = OpenAQ(api_key=API_KEY)

CACHE_DIR = 'data'

def get_country_by_name(selected_country):
    try:
        countries = client.countries.list(
            limit=200
        )
        for country in countries.results:
            if selected_country.lower().strip() == country.name.lower():
                return country.id
        return f'Cannot find results for {selected_country}'
    except Exception as e: 
        return f"Error finding countris: {e}"
    
def get_daily_data_by_country(selected_country, country_id, days=1): # for one day only, just like the one we get from IQAIR
    cache_file = os.path.join(CACHE_DIR, f'cache_{country_id}_{days}d.json')
    
    # 1. Check Cache
    if os.path.exists(cache_file):
        print(f"Loading data from cache: {cache_file}")
        try:
            df = pd.read_json(cache_file, orient='records') # orient='records':  the DataFrame is converted into a list of dictionaries, where each dictionary represents a row in the DataFrame.
            return df
        
        except Exception as e:
            print(f"Error loading cache: {e}")

    print(f"Fetching data for {selected_country} (Last {days} days)...")

    # 2. Fetch Data
        # Get top locations (limit to 10 and then mean/median of them)
    locations = client.locations.list(
        countries_id=country_id,
        parameters_id=2, # 2: PM2.5
        limit=10
    )
    
    datefrom = datetime.now() - timedelta(days=days) 

    available_results = []

    print(f"Found {len(locations.results)} in {selected_country}")

    location_count = 0
    for location in locations.results:
        if location_count >= 10:  # Stop after 10 locations
            break

        try:
            sensor_id = None
            # DONT TAKE THESE
            # measurements = client.measurements.list(
            #     sensors_id=sensor_id,
            #     datetime_from=datefrom
            # )
            for sensor in location.sensors:
                if sensor.parameter.id == 2: # id 2 in PM2.5 (we only take PM2.5)
                    sensor_id = sensor.id
                    # print(location.name, sensor_id)
                    break

            if sensor_id:
                
                measurements = client.measurements.list(
                    sensors_id=sensor_id,
                    datetime_from=datefrom,
                    limit=1000 # limit the hourly data
                )
                if measurements.results:

                    for m in measurements.results:
                        available_results.append({
                            'name': location.name,
                            'time_to': m.period.datetime_to.local,
                            'value': m.value
                        })

                    location_count += 1
                
        except Exception as e:
            print(f"Error fetching for location {location.id}: {e}")
            continue
    if not available_results:
        raise Exception("No data found for this country.")

    # return available_results # returns a list of dictionaries of each hour of each of the 10 locations

    # 3. Aggregate
    df = pd.DataFrame(available_results)

    # Ensure datetime conversion with UTC to handle timezone aware strings
    df['time_to'] = pd.to_datetime(df['time_to'])

    # Resample to hourly average across all stations
    # First, round time to nearest hour
    df['time_to'] = df['time_to'].dt.floor('h')

    # Group by time and take mean
    df_agg = df.groupby('time_to')['value'].mean().reset_index()
    df_agg.sort_values('time_to')

    # Convert PM2.5 values to AQI
    df_agg['aqi'] = df_agg['value'].apply(lambda x: aqi.to_aqi([(aqi.POLLUTANT_PM25, x)], algo=aqi.ALGO_EPA))
    df_agg['time_to'] = pd.to_datetime(df['time_to'])
    
    # 4. Save to Cache
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    df_agg.to_json(cache_file, orient='records', date_format='iso')

    return df_agg # returns: sth like 23 2025-12-01 15:00:00+07:00  15.024756

def get_historic_data_by_country(selected_country, country_id, days=30): 
    cache_file = os.path.join(CACHE_DIR, f'cache_{country_id}_{days}d.json')
    
    # 1. Check Cache
    if os.path.exists(cache_file):
        print(f"Loading data from cache: {cache_file}")
        try:
            df = pd.read_json(cache_file, orient='records') # orient='records':  the DataFrame is converted into a list of dictionaries, where each dictionary represents a row in the DataFrame.
            return df
        except Exception as e:
            print(f"Error loading cache: {e}")

    print(f"Fetching data for {selected_country} (Last {days} days)...")

    # 2. If no cache, fetch Data
        # Get top locations (limit to 10 and then mean/median of them)
    locations = client.locations.list(
        countries_id=country_id,
        parameters_id=2, # 2: PM2.5
        limit=20
    )
    
    datefrom = datetime.now() - timedelta(days=days) 

    available_results = []

    print(f"Found {len(locations.results)} stations in {selected_country}")

    location_count = 0
    for location in locations.results:
        # print(f"Found {location.name}") # for debugging
        if location_count >= 10:  # Stop after 10 locations
            break

        try:
            sensor_id = None
            for sensor in location.sensors:
                if sensor.parameter.id == 2: # id 2 in PM2.5 (we only take PM2.5)
                    sensor_id = sensor.id
                    # print(f"Found sensor: {sensor_id}")
                    break

            if sensor_id:
                page = 1 # Pagination
                while True:
                    try:
                        measurements = client.measurements.list(
                            sensors_id=sensor_id,
                            datetime_from=datefrom,
                            limit=1000,
                            page=page
                        )

                        if not measurements.results:
                            break
                        
                        # print(f"Got {location.name} measurements!")
                        for m in measurements.results:
                            available_results.append({
                                # 'name': location.name,
                                'time_to': m.period.datetime_to.local,
                                'value': m.value
                            })
                        # print(f"Appended {location.name} at page {page}!")

                        page += 1
                        # Safety break
                        if page > 200:
                            break 
                    except Exception as e:
                        print(f"Error fetching page {page} for location {location.name}: {e}")
                        break
                location_count += 1
                # print(f"Done {location_count} station")
                
        except Exception as e:
            print(f"Error fetching for location {location.id}: {e}")
            continue
    if not available_results:
        raise Exception("No data found for this country.")
    
    # return available_results # returns a list of dictionaries of each hour of each of the 10 locations

    # 3. Aggregate
    df = pd.DataFrame(available_results)

    # Ensure datetime conversion with UTC to handle timezone aware strings
    df['time_to'] = pd.to_datetime(df['time_to'])

    # Resample to hourly average across all stations
    # First, round time to nearest hour
    df['time_to'] = df['time_to'].dt.floor('h')

    # Group by time and take mean
    df_agg = df.groupby('time_to')['value'].mean().reset_index()
    df_agg.sort_values('time_to')

    # Convert PM2.5 values to AQI
    df_agg['aqi'] = df_agg['value'].apply(lambda x: aqi.to_aqi([(aqi.POLLUTANT_PM25, x)], algo=aqi.ALGO_EPA))
        
    # 4. Save to Cache
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    df_agg.to_json(cache_file, orient='records', date_format='iso')

    return df_agg # returns: sth like 23 2025-12-01 15:00:00+07:00  15.024756

def get_ranking_by_country(country_id):
    cache_file = os.path.join(CACHE_DIR, f'cache_{country_id}_ranking.json')
    
    if os.path.exists(cache_file):
        print(f"Loading data from cache: {cache_file}")
        try:
            df = pd.read_json(cache_file, orient='records') # orient='records':  the DataFrame is converted into a list of dictionaries, where each dictionary represents a row in the DataFrame.
            return df
        except Exception as e:
            print(f"Error loading cache: {e}")

    else:
        locations = client.locations.list(
            countries_id=country_id,
            parameters_id=2,
            limit=60
        )

        date_from = datetime.now() - timedelta(hours=1)
        
        available_results = []

        location_count = 0
        for location in locations.results:
            if location_count >= 10:
                break

            sensor_id = None
            for sensor in location.sensors:
                if sensor.parameter.id == 2: # id 2 in PM2.5 (we only take PM2.5)
                    sensor_id = sensor.id
                    break

            measurements = client.measurements.list(
                sensors_id=sensor_id,
                datetime_from=date_from
            )

            if measurements.results:
                latest = measurements.results[-1]
                # formatted_time_from = pd.to_datetime(latest.period.datetime_from.local).strftime("%Y-%m-%d %H:%M")
                formatted_time_to = pd.to_datetime(latest.period.datetime_to.local).strftime("%Y-%m-%d %H:%M")

                available_results.append({
                    'name': location.name,
                    'value': latest.value,
                    # 'units': latest.parameter.units, # Will no need unit when we work on AQI!!!
                    # 'time_from': formatted_time_from,
                    'time_to': formatted_time_to
                })
                location_count += 1

        available_results.sort(key=lambda x: x['value'], reverse=True)

        # print("\n--- Air Quality Ranking (Highest PM2.5) ---")
        # for index, result in enumerate(available_results, 1):
        #     print(f"{index}. {result['name']}: {result['value']:.2f} {result['units']} at {result['time']}")

        df = pd.DataFrame([
            {
                'time_to': result['time_to'],
                'name': result['name'],
                'value': result['value'],
            }
            for result in available_results
        ])
        df['aqi'] = df['value'].apply(lambda x: aqi.to_aqi([(aqi.POLLUTANT_PM25, x)], algo=aqi.ALGO_EPA))

        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

        df.to_json(cache_file, orient='records', date_format='iso')

        return df

def get_kpi_card(selected_country, df):
    average_value = df['value'].mean().mean()
    # first .mean() computes mean of each row in column ['value'], second .mean() computes mean of each value of the only column of df['value'].mean()
    pm25_aqi = aqi.to_aqi([(aqi.POLLUTANT_PM25, average_value)], algo=aqi.ALGO_EPA)
    
    if pm25_aqi < 51:
        status = 'Good'
    elif pm25_aqi < 101:
        status = 'Moderate'
    elif pm25_aqi < 151:
        status = 'Unhealthy for sensitive groups'
    elif pm25_aqi < 201:
        status = 'Unhealthy'
    elif pm25_aqi < 301:
        status = 'Very Unhealthy'
    else:
        status = 'Hazardous'
    
    print(f"{selected_country.capitalize()} Air Quality Index")
    # print(f"Last updated at {df['time_to'].max().time()}, {df['time_to'].max().date()} Local Time")
    print("\n╔══════════════════════════════════════════╗")
    print(f"║       {pm25_aqi}              {status}           ║")
    print(f"║     US AQI       PM2.5 | {average_value:.2f} µg/m³     ║")
    print("╚══════════════════════════════════════════╝\n")

# print(get_daily_data_by_country('Cambodia', 57, 1))
# print(get_historic_data_by_country('Cambodia', 57, 30))
# print(get_ranking_by_country(57))