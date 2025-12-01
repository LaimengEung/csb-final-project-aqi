from module.openaq_api import *

def main():
    print("\n╔═════════════════════════════════════╗")
    print("║         AIR QUALITY MONITOR         ║")
    print("╚═════════════════════════════════════╝\n")

    search_country = input("Enter your country name: ")
    country_id = get_country_by_name(search_country)
    data = get_daily_data_by_country(country_id)
    print(data)
    get_kpi_card(search_country, data)

main()