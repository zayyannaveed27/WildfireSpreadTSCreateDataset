# AI for Disaster Management Dataset

This repository contains the code to recreate the dataset for the senior thesis submission **"Advancing Wildfire Forecasting: A Multimodal Dataset for Pretraining Baseline Models in Disaster Prediction"**.

## Overview

The main goal of this project is to create a multimodal dataset for wildfire prediction by leveraging data from Google Earth Engine (GEE) and integrating it with multiple data sources like satellite imagery, elevation models, and weather forecasts.

## Requirements

To recreate the dataset, you will need:
- Access to Google Cloud Storage.
- Access to Google Earth Engine.
- Python and the required libraries.

## Setup Instructions

1. Install all necessary Python dependencies from the `requirements.txt` file:
   ```
   pip install -r requirements.txt
   ```

2. Set up the [Google Cloud SDK](https://cloud.google.com/sdk/docs/how-to) and authenticate with your Google account:
   ```
   gcloud auth login
   ```

3. Set up the [Google Earth Engine Python API](https://developers.google.com/earth-engine/guides/python_install) and authenticate:
   ```
   earthengine authenticate
   ```

4. Add your [Google Service Account](https://cloud.google.com/iam/docs/service-account-overview) credentials to a `.env` file. Example `.env` file:
   ```
   GEE_KEY_FILE=<path_to_service_account_key.json>
   GEE_SERVICE_ACCOUNT=<service_account_email>
   ```

5. Update the configuration file `config/US_polygons.json` with the feature collection of sub-regions in the US.

## Usage

To run the script and create the dataset for a specific year and timeframe:
```bash
python script_name.py <year> [--start_month <1-12>] [--end_month <1-12>] [--output_dir <output_directory>]
```

### Example
To generate data for June through August 2024 and store it in the `data/fire_images` directory:
```bash
python script_name.py 2024 --start_month 6 --end_month 8 --output_dir data/fire_images
```

## Notes

- Ensure your `.env` file is properly configured with GEE credentials.
- Large datasets may require increased storage space and network bandwidth.

For any issues or questions, please contact the repository maintainer.

