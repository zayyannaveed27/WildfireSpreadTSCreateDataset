import os
import ee
import json
from DataPreparation.satellites.FirePred import FirePred
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
import argparse
import json
from io import StringIO
import asyncio
import aiohttp

def prepare_daily_image(geometry, date_of_interest: str, time_stamp_start="00:00", time_stamp_end="23:59"):
    """Prepare a daily image collection from the FirePred satellite client."""
    satellite_client = FirePred()
    img = satellite_client.compute_daily_features(
        date_of_interest + 'T' + time_stamp_start,
        date_of_interest + 'T' + time_stamp_end,
        geometry
    )
    return img

async def fetch_url(session, url, date_of_interest):
    """Asynchronously fetch CSV data from a URL."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                csv_data = await response.text()
                if csv_data.strip():
                    data = pd.read_csv(StringIO(csv_data))
                    data['date'] = date_of_interest
                    return data
                else:
                    print(f"No data for date {date_of_interest}")
            else:
                print(f"Failed to fetch data for {date_of_interest}, status: {response.status}")
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

async def process_region_async(sub_region_polygon, date_of_interest, session, csv_path, sub_region_number=-1):
    """Asynchronously process a single region."""
    try:
        feature_image = prepare_daily_image(sub_region_polygon, date_of_interest)
        sampled_pixels = feature_image.sample(
            region=sub_region_polygon,
            scale=375,
            geometries=True
        )
        url = sampled_pixels.getDownloadURL("CSV")
        data =  await fetch_url(session, url, date_of_interest)
        if data is not None and sub_region_number != -1:
            print(f"Saving data for sub-region {sub_region_number} on {date_of_interest}.")
            save_to_csv(data, csv_path)  # Save data immediately
        return data
    except Exception as e:
        print(f"Error processing region for date {date_of_interest}: {e}")
    return None

async def process_day(test_geometry, region_geometries, date_of_interest, csv_path):
    """Asynchronously process all regions for a single day."""
    semaphore = asyncio.Semaphore(30)  # Limit concurrent requests to 30
    async with aiohttp.ClientSession() as session:
        # Process test region
        test_data = await process_region_async(test_geometry, date_of_interest, session, csv_path)

        if test_data is not None:
            print(f"Test region successful for date {date_of_interest}. Proceeding to other regions.")

            # Create tasks for all sub-regions
            tasks = [
                process_region_async(geometry, date_of_interest, session, csv_path, sub_region_number)
                for sub_region_number, geometry in enumerate(region_geometries, start=1)
            ]

            # Gather results
            await asyncio.gather(*tasks, return_exceptions=True)

            # # Filter valid data
            # valid_data = [data for data in region_data if data is not None and not isinstance(data, Exception)]
            # if valid_data:
            #     return pd.concat(valid_data, ignore_index=True)
        else:
            print(f"Test region failed for date {date_of_interest}. Skipping other regions.")


def save_to_csv(daily_data, csv_path):
    """Save daily data to the CSV file."""
    if daily_data is not None and not daily_data.empty:
        # Check if file exists
        if not os.path.isfile(csv_path):
            daily_data.to_csv(csv_path, mode='w', index=False, header=True)
        else:
            daily_data.to_csv(csv_path, mode='a', index=False, header=False)

def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, help="Year for which to process data")
    parser.add_argument("--end_month", type=int, default=12, help="Ending month (inclusive), default is December")
    parser.add_argument("--start_month", type=int, default=1, help="Starting month (inclusive), default is January")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    key_file = os.getenv("GEE_KEY_2_FILE")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT_2")

    # Initialize Earth Engine
    credentials = ee.ServiceAccountCredentials(service_account, key_file)
    ee.Initialize(credentials)

    # Load sub-regions
    with open('US_subregion_polygons_1.5.json', 'r') as f:
        sub_regions = json.load(f)
    # Convert all sub-regions to geometries
    region_geometries = []
    for i, sub_region in enumerate(sub_regions):
        try:
            region_geometries.append(ee.Geometry.Polygon(sub_region['coordinates']))
        except ee.EEException as e:
            print(f"Skipping invalid geometry for sub-region {i}: {e}")

    test_region = {"type": "Polygon", "coordinates": [[[-120.18038929064562, 34.08212402766836], [-120.18038929064565, 34.546812350183046], [-122.13017156536749, 34.5710657437825], [-120.18038929064562, 34.08212402766836]]]}
    test_geometry = ee.Geometry.Polygon(test_region['coordinates'])

    # Prepare CSV path
    year = args.year
    start_month = args.start_month
    end_month = args.end_month
    csv_path = f"TimeSeries/{year}.csv"

    # Process each day in the range
    for month in range(start_month, end_month + 1):
        month_start = datetime(year, month, 1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        month_end = next_month - timedelta(days=1)

        print(f"Processing data for {year}-{month:02d}")

        current_date = month_start
        while current_date <= month_end:
            date_of_interest = current_date.strftime('%Y-%m-%d')
            print(f"Processing data for {date_of_interest}")
            asyncio.run(process_day(test_geometry, region_geometries, date_of_interest, csv_path))
            # save_to_csv(daily_data, csv_path)
            current_date += timedelta(days=1)

if __name__ == '__main__':
    main()