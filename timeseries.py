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

# Load environment variables from .env file
load_dotenv()

# Initialize Google Earth Engine
key_file = os.getenv("GEE_KEY_FILE")
service_account = os.getenv("GEE_SERVICE_ACCOUNT")
credentials = ee.ServiceAccountCredentials(service_account, key_file)
ee.Initialize(credentials)


def prepare_daily_image(geometry, date_of_interest:str, time_stamp_start:str="00:00", time_stamp_end:str="23:59"):
    """_summary_

    Args:
        date_of_interest (str): _description_ Date for which we want to download data.
        time_stamp_start (str, optional): _description_. String representation of start of day time. Defaults to "00:00".
        time_stamp_end (str, optional): _description_. String representation of end of day time. Defaults to "23:59".

    Returns:
        _type_: _description_ Extracted image collection.
    """        """"""
    

    satellite_client = FirePred()
    img_collection = satellite_client.compute_daily_features(date_of_interest + 'T' + time_stamp_start,
                                                                date_of_interest + 'T' + time_stamp_end,
                                                                geometry)
    img = img_collection.mosaic()       
    return img


# Load the sub-regions from the json file
with open('US_subregion_polygons.json', 'r') as f:
    sub_regions = json.load(f)


# Dictionary for each month's start and end dates in 2022
month_dates_2022 = {
    # "January": {"start_date": datetime(2022, 1, 1), "end_date": datetime(2022, 1, 31)},
    # "February": {"start_date": datetime(2022, 2, 1), "end_date": datetime(2022, 2, 28)},
    "March": {"start_date": datetime(2022, 3, 1), "end_date": datetime(2022, 3, 31)},
    "April": {"start_date": datetime(2022, 4, 1), "end_date": datetime(2022, 4, 30)},
    "May": {"start_date": datetime(2022, 5, 1), "end_date": datetime(2022, 5, 31)},
    "June": {"start_date": datetime(2022, 6, 1), "end_date": datetime(2022, 6, 30)},
    "July": {"start_date": datetime(2022, 7, 1), "end_date": datetime(2022, 7, 31)},
    "August": {"start_date": datetime(2022, 8, 1), "end_date": datetime(2022, 8, 31)},
    "September": {"start_date": datetime(2022, 9, 1), "end_date": datetime(2022, 9, 30)},
    "October": {"start_date": datetime(2022, 10, 1), "end_date": datetime(2022, 10, 31)},
    "November": {"start_date": datetime(2022, 11, 1), "end_date": datetime(2022, 11, 30)},
    "December": {"start_date": datetime(2022, 12, 1), "end_date": datetime(2022, 12, 31)},
}

# Print the dictionary to verify
for month, dates in month_dates_2022.items():
    month_data = []
    start_date = dates['start_date']
    end_date = dates['end_date']
    current_date = start_date
    print(f"Processing data for {month}")

    while current_date <= end_date:
        date_of_interest = current_date.strftime('%Y-%m-%d')
        current_date += timedelta(days=1)

        for i, sub_region in enumerate(sub_regions):
            
            # take the first sub region and prepare the daily image
            sub_region_polygon = ee.Geometry.Polygon(sub_regions[0]['coordinates'])

            feature_image = prepare_daily_image(sub_region_polygon, date_of_interest)

            # Sample each pixel within the geometry to get individual pixel values
            sampled_pixels = feature_image.sample(
                region=sub_region_polygon,
                scale=375,  # Set according to the dataset's resolution
                geometries=True, # Include pixel coordinates
            )

            # Export to CSV locally
            url = sampled_pixels.getDownloadURL("CSV")
            response = requests.get(url)

            # Check if the request was successful
            if response.status_code == 200:
                # Decode the binary data to a string and load it into a DataFrame
                csv_data = response.content.decode('utf-8')
                data = pd.read_csv(StringIO(csv_data))
                month_data.append(data)
            else:
                print(f"Failed to download data for sub-region {i+1}: {response.status_code}")

    # Concatenate all data into a single DataFrame
    combined_data = pd.concat(month_data, ignore_index=True)

    # Save the combined data to a CSV file
    csv_path = "/TimeSeries" + start_date + "_" + end_date + ".csv"
    combined_data.to_csv(csv_path, index=False)