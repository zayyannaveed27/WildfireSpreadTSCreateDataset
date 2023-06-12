import ee
import yaml
import tqdm

from DataPreparation.DatasetPrepareService import DatasetPrepareService

if __name__ == '__main__':

    with open("config/us_fire_2021_1e7.yml", "r", encoding="utf8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    key_file = 'your_gcloud_key_file.json'

    service_account = 'yourname@yourbucket.iam.gserviceaccount.com'
    credentials = ee.ServiceAccountCredentials(service_account, key_file)
    ee.Initialize(credentials)
    satellites = ['FirePred']

    fire_names = list(config.keys())
    for non_fire_key in ["output_bucket", "rectangular_size", "year"]:
        fire_names.remove(non_fire_key)
    locations = fire_names

    generate_goes = False
    mode = 'viirs'

    failed_locations = []

    for location in tqdm.tqdm(locations):
        print(f"Failed locations so far: {failed_locations}")
        dataset_pre = DatasetPrepareService(location=location, config=config)
        print("Current Location:" + location)

        try:
            dataset_pre.download_dataset_to_gcloud(satellites, '32610', False, n_buffer_days=4)
            # Uncomment for local download
            # dataset_pre.batch_downloading_from_gclound_training(satellites)
        except:
            failed_locations.append(location)
