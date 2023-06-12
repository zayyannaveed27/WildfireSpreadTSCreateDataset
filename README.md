# WildfireSpreadTS - Dataset creation

To create the dataset, you will need access to Google Cloud Storage and Google Earth Engine. 

1. Install all necessary requirements from the requirements.txt file via 
```
pip install -r requirements.txt
```
2. Set up the Google Cloud SDK and authenticate with your Google account.
3. Set up the Google Earth Engine Python API and authenticate with your Google account.
4. Enter your Google Service Account credentials the path to your key file in `main.py`.
5. Set the yaml file in main.py that you want to use to download corresponding data and run `python main.py`.

The yaml files in `config` contain only the pre-filtered fires that were used in creating the dataset. 


