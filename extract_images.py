'''
Asynchronous Fire Image Processing with Google Earth Engine

This script processes satellite imagery using Google Earth Engine for US during specific time periods. It:

1. Prepares daily image collections from the FirePred satellite client.
2. Downloads images for specific dates and regions in GeoTIFF format.
3. Uses asynchronous programming to efficiently handle multiple requests to Google Earth Engine.

Usage:
    python script_name.py <year> [--start_month <1-12>] [--end_month <1-12>] [--output_dir <output_directory>] 

Example:
    python script_name.py 2024 --start_month 6 --end_month 8 --output_dir data/fire_images 

Ensure you have the necessary Google Earth Engine credentials and .env file configured with:
    GEE_KEY_FILE=<path_to_key_file>
    GEE_SERVICE_ACCOUNT=<service_account_email>
'''

import os
import ee
import json
from DataClasses.satellites.FirePred import FirePred
from datetime import datetime, timedelta
from dotenv import load_dotenv
import argparse
import asyncio
import aiohttp

# limit for Google Earth Engine http requests
REQUEST_LIMIT = 30
# config file containing the feature collection of sub regions in US
GEOJSON_FILE = "config/US_polygons.json"

def prepare_daily_image(geometry, date_of_interest: str, time_stamp_start="00:00", time_stamp_end="23:59"):
    """Prepare a daily image collection from the FirePred satellite client."""
    satellite_client = FirePred()
    img = satellite_client.compute_daily_features(
        date_of_interest + 'T' + time_stamp_start,
        date_of_interest + 'T' + time_stamp_end,
        geometry
    )
    return img

async def download_image(session, url, output_filename):
    """
    Asynchronously download an image from the given URL and save it to a local file.
    """

    async with session.get(url) as response:
        if response.status == 200:
            with open(output_filename, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
            print(f"Image successfully downloaded to {output_filename}")
        else:
            print(f"Failed to download image. HTTP status code: {response.status}")

async def process_region_async(semaphore, sub_region_polygon, date_of_interest, session, output_dir, sub_region_number):
    """Asynchronously process a single region on Google Earth Engine with semaphore-controlled concurrency."""
    async with semaphore:
        try:
            feature_image = prepare_daily_image(sub_region_polygon, date_of_interest)

            download_url = feature_image.getDownloadURL({
                'scale': 375,
                # 'crs': 'ESPG:32610',
                'region': sub_region_polygon,
                'format': 'GeoTIFF',  # Specify GeoTIFF format
                'maxPixels': 1e13  # Increase max pixels if needed
            })

            # Dynamically generate the output filename based on the current date
            output_filename = f"{output_dir}/{date_of_interest}_{sub_region_number}.tif"
            
            print(f"Downloading image {output_filename} from: {download_url}")
            await download_image(session, download_url, output_filename)

        except Exception as e:
            print(f"Error processing region {sub_region_number} for date {date_of_interest}: {e}")
        return None


async def process_day(region_geometries, date_of_interest, output_dir):
    """Asynchronously process all regions for a single day."""
    semaphore = asyncio.Semaphore(REQUEST_LIMIT)  # Limit concurrent requests to 30
    async with aiohttp.ClientSession() as session:

        print(f"Processing data for all regions for {date_of_interest}.")

        # Create tasks for all sub-regions
        tasks = [
            process_region_async(semaphore, geometry, date_of_interest, session, output_dir, sub_region_number)
            for sub_region_number, geometry in enumerate(region_geometries, start=1)
        ]

        await asyncio.gather(*tasks, return_exceptions=True)



def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, help="Year for which to process data")
    parser.add_argument("--output_dir", default="data", help="output directory for storing the downloaded images")
    parser.add_argument("--end_month", type=int, default=12, help="Ending month (inclusive), default is December")
    parser.add_argument("--start_month", type=int, default=1, help="Starting month (inclusive), default is January")
    args = parser.parse_args()

    # Initialize the time range
    year = args.year
    start_month = args.start_month
    end_month = args.end_month

    output_dir = args.output_dir

    # Load Google Earth Engine credentials
    load_dotenv()
    key_file = os.getenv("GEE_KEY_FILEPATH")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT")

    # Initialize Earth Engine
    credentials = ee.ServiceAccountCredentials(service_account, key_file)
    ee.Initialize(credentials)

    # Load sub-regions in US
    with open(GEOJSON_FILE, 'r') as f:
        sub_regions = json.load(f)

    region_geometries = []
    # Iterate through the polygons and create ee.Geometry.Polygon objects
    for i, sub_region in enumerate(sub_regions['features']):  
        try:
            coordinates = sub_region['geometry']['coordinates']
            region_geometries.append(ee.Geometry.Polygon(coordinates))
        except KeyError as e:
            print(f"Skipping sub-region {i} due to missing key: {e}")
        except ee.EEException as e:
            print(f"Skipping invalid geometry for sub-region {i}: {e}")

    # Process each day in the time range
    for month in range(start_month, end_month + 1):
        month_start = datetime(year, month, 1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        month_end = next_month - timedelta(days=1)

        print(f"Processing data for {year}-{month:02d}")

        current_date = month_start
        while current_date <= month_end:
            date_of_interest = current_date.strftime('%Y-%m-%d')
            print(f"Processing data for {date_of_interest}")
            asyncio.run(process_day(region_geometries, date_of_interest, output_dir))
            current_date += timedelta(days=1)


if __name__ == '__main__':
    main()
