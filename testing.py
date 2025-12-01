from openaq import OpenAQ
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENAQ_API_KEY')
client = OpenAQ(api_key=API_KEY)

def visualisation():
    pass

def get_data_by_country(country_id): # for one day only, just like the one we get from IQAIR
    locations = client.locations.list(
        countries_id=country_id,
        parameters_id=2,
        limit=60
    )

    datefrom = datetime.now() - timedelta(days=1)

    available_results = []

    for location in locations.results:
        sensor_id = location.sensors[1].id
        measurements = client.measurements.list(
            sensors_id=sensor_id,
            datetime_from=datefrom
        )

        if measurements.results:
            latest = measurements.results[-1]
            formatted_time_from = pd.to_datetime(latest.period.datetime_from.local).strftime("%Y-%m-%d %H:%M")
            formatted_time_to = pd.to_datetime(latest.period.datetime_to.local).strftime("%Y-%m-%d %H:%M")

            available_results.append({
                'name': location.name,
                'value': latest.value,
                'units': latest.parameter.units, # Will no need unit when we work on AQI!!!
                'time_from': formatted_time_from,
                'time_to': formatted_time_to
            })

    available_results.sort(key=lambda x: x['value'], reverse=True)

    # print("\n--- Air Quality Ranking (Highest PM2.5) ---")
    # for index, result in enumerate(available_results, 1):
    #     print(f"{index}. {result['name']}: {result['value']:.2f} {result['units']} at {result['time']}")

    df = pd.DataFrame([
        {
            'time_from': result['time_from'],
            'time_to': result['time_to'],
            'name': result['name'],
            'value': result['value'],
            'units': result['units']
        }
        for result in available_results
    ])

    return df
        # If found, use mean to get the DISPLAY PM2.5 value or AQI (When we actually do the project)


def get_country_by_name(selected_country):
    countries = client.countries.list(
        limit=60
    )
    
    try:
        for country in countries.results:
            if selected_country.lower().strip() == country.name.lower():
                return country.id
    except: 
        return f"Cannot find results for {selected_country}"

def search_country_id(country_id, date_to): # Just a simple!!!!
    response = client.locations.list(
        countries_id=country_id,
        parameters_id=2,
        limit=60
    )

    # Time
    # date_to = datetime.now()
    date_from = date_to - timedelta(days=1) # 7 days

    results = response.results

    print(f"Found {len(results)} stations in {results[1].country.name}")
    available_results = [] # list of dictionaries which contains {'name':, "value":, "time":}

    # index = 1
    for location in response.results:
        # try:
            # Find the PM2.5 sensor
        sensor_id = None
        for sensor in location.sensors:
            if sensor.parameter.id == 2:
                sensor_id = sensor.id
                print(sensor)
                break
            
    # for location in response.results:
    #     sensor_id = location.sensors[1].id
    #     measurements = client.measurements.list(
    #         sensors_id=sensor_id,
    #         datetime_from=date_from
    #     )
    #     if measurements.results:
    #         latest = measurements.results[-1]
    #         formatted_local_time = pd.to_datetime(latest.period.datetime_to.local).strftime("%Y-%m-%d %H:%M")

    #         available_results.append({
    #             'name': location.name,
    #             'value': latest.value,
    #             'units': latest.parameter.units,
    #             'time': formatted_local_time
    #         })

    #         # print(f"{index}. {location.name}: {latest.value:.2f} {latest.parameter.units} at {formatted_local_time}")

    #         # index += 1        

    # # Sort by value (highest to lowest)
    # available_results.sort(key=lambda x: x['value'], reverse=True)

    # print("\n--- Air Quality Ranking (Highest PM2.5) ---")
    # for index, result in enumerate(available_results, 1):
    #     print(f"{index}. {result['name']}: {result['value']:.2f} {result['units']} at {result['time']}")

def main():
    print("Welcome to the Open Air Quality Monitor System")
    selected_country = input("Enter your a country: ")
    user_country_id = get_country_by_name(selected_country)
    
    user_date = pd.to_datetime(input("Input the date (YYYY-mm-dd): "))

    visualisation()

    print(search_country_id(user_country_id, user_date))
    # print(get_data_by_country(user_country_id))
main()