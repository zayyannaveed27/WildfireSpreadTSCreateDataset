import ee
import yaml
import tqdm
import argparse
import os

from DataPreparation.DatasetPrepareService import DatasetPrepareService
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# if __name__ == '__main__':

#     # TODO: Enter your desired config file path here. If you just want to recreate the results from the paper, 
#     # use the config files in the config folder to download the data belonging to the specified year. 
#     with open("config/us_fire_2021_1e7.yml", "r", encoding="utf8") as f:
#         config = yaml.load(f, Loader=yaml.FullLoader)

#     # TODO: Enter your gcloud key file path here.
#     key_file = 'your_gcloud_key_file.json'

#     # TODO: Enter your gcloud service account here.
#     service_account = 'yourname@yourbucket.iam.gserviceaccount.com'
#     credentials = ee.ServiceAccountCredentials(service_account, key_file)
#     ee.Initialize(credentials)

#     # Number of days to extract additionally, before and after the fire dates given in GlobFire. 
#     # If we want to perform multi-temporal modeling, e.g. with five days of input data, based on which we want to
#     # predict the fire occurrence on the sixth day, we need to add four days before the first fire occurrence. This way,
#     # we can predict the fire spread right on the day after the fire first appears. Alternatively, the preceding input 
#     # data could of course be set to zero. However, in a real-world scenario, we would *always* have preceding data,
#     # so we choose to model it this way here. Similarly, we want the last fire date to be able to take every position
#     # in the input data, so we add four days after the last fire date, to 'push out' the last fire date.
#     N_BUFFER_DAYS = 4

#     # Extract fire names from config file.
#     fire_names = list(config.keys())
#     for non_fire_key in ["output_bucket", "rectangular_size", "year"]:
#         fire_names.remove(non_fire_key)
#     locations = fire_names

#     # Keep track of any failures happening, to be able to manually re-run these later.
#     # Shouldn't happen, but if it does, we get to know about it.
#     failed_locations = []

#     # Tell Google Earth Engine to compute the images and add them to the specified google cloud bucket.
#     for location in tqdm.tqdm(locations):
#         print(f"Failed locations so far: {failed_locations}")
#         dataset_pre = DatasetPrepareService(location=location, config=config)
#         print("Current Location:" + location)

#         try:
#             dataset_pre.extract_dataset_from_gee_to_gcloud('32610', n_buffer_days=N_BUFFER_DAYS)
#             # Uncomment to download data from gcloud to the local machine right away. Alternatively, you can use the
#             # gcloud command line tool to download the whole dataset at once after this script is done. 
#             dataset_pre.download_data_from_gcloud_to_local()
#         except:
#             failed_locations.append(location)

def process_location(location, config, failed_locations):
    """Function to process a single location and handle exceptions."""
    try:
        dataset_pre = DatasetPrepareService(location=location, config=config)
        print("Current Location:" + location)
        dataset_pre.extract_dataset_from_gee_to_gcloud('32610', n_buffer_days=N_BUFFER_DAYS)
    except Exception as e:
        print(f"Error processing location {location}: {e}")
        failed_locations.append(location)


if __name__ == '__main__':

    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("config_file_path", help="path to config file in .yml format")
    args = parser.parse_args()

    # Load the config file
    with open(args.config_file_path, "r", encoding="utf8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # Initialize Google Earth Engine
    key_file = os.getenv("GEE_KEY_FILE")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT")
    credentials = ee.ServiceAccountCredentials(service_account, key_file)
    ee.Initialize(credentials)

    # Set buffer days
    N_BUFFER_DAYS = 4

    # Extract fire names from the config file
    fire_names = list(config.keys())
    for non_fire_key in ["output_bucket", "rectangular_size", "year"]:
        fire_names.remove(non_fire_key)
    locations = fire_names

    print(len(locations))
    print(locations[0])

    failed_locations = []

    # Use ThreadPoolExecutor to run the tasks in parallel
    max_threads = 20  # You can adjust this number based on your system's capabilities
    with ThreadPoolExecutor(max_threads) as executor:

        futures = {executor.submit(process_location, location, config, failed_locations): location for location in locations}

        # Use tqdm to show the progress
        for future in tqdm.tqdm(as_completed(futures), total=len(locations)):
            location = futures[future]
            try:
                future.result()  # This will raise any exception that occurred during execution
            except Exception as e:
                print(f"Error in future for location {location}: {e}")
    
    print(f"Failed locations: {failed_locations}")
