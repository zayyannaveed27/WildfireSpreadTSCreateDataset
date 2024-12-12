'''
US Grid Generator Using Google Earth Engine

This script generates a grid of polygons covering the United States and filters them to include only those
that intersect with an accurate US boundary geometry and saves them as a json object in "config/US_polygons.json".

'''

import os
import ee
from dotenv import load_dotenv
import json

if __name__ == '__main__':

    load_dotenv()
    key_file = os.getenv("GEE_KEY_FILEPATH")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT")
    credentials = ee.ServiceAccountCredentials(service_account, key_file)
    # Initialize the Earth Engine API
    ee.Initialize(credentials)

    # Define the accurate US geometry (as provided)
    us_geometry = ee.Geometry.Polygon(
        [[[-125.1803892906456, 35.26328285844432],
        [-117.08916345892665, 33.2311514593429],
        [-114.35640058749676, 32.92199940444295],
        [-110.88773544819885, 31.612036247094473],
        [-108.91086200144109, 31.7082477979397],
        [-106.80030780089378, 32.42079476218232],
        [-103.63413436750255, 29.786401496314422],
        [-101.87558377066483, 30.622527701868453],
        [-99.40039768482492, 28.04018292597704],
        [-98.69085295525215, 26.724810345780593],
        [-96.42355704777482, 26.216515704595633],
        [-80.68508661702214, 24.546812350183075],
        [-75.56173032587596, 26.814533788629998],
        [-67.1540159827795, 44.40095539443753],
        [-68.07548734644243, 46.981170472447374],
        [-69.17500995805074, 46.98158998130476],
        [-70.7598785138901, 44.87172183866657],
        [-74.84994741250935, 44.748084983808],
        [-77.62168256782745, 43.005725611950055],
        [-82.45987924104175, 41.41068867019324],
        [-83.38318501671864, 42.09979904377044],
        [-82.5905167831457, 45.06163491639556],
        [-84.83301910769038, 46.83552648258547],
        [-88.26350848510909, 48.143646480291835],
        [-90.06706251069104, 47.553445811024204],
        [-95.03745451438925, 48.9881557770297],
        [-98.45773319567587, 48.94699366043251],
        [-101.7018751401119, 48.98284560308372],
        [-108.43164852530356, 48.81973606668503],
        [-115.07339190755627, 48.93699058308441],
        [-121.82530604190744, 48.9830983403776],
        [-122.22085227110232, 48.63535795404536],
        [-124.59504332589562, 47.695726563030405],
        [-125.1803892906456, 35.26328285844432]]])

    # Define grid parameters
    min_lng, min_lat, max_lng, max_lat = -125.5, 24.5, -65.5, 49.5  # Extended bounds
    cell_size = 1.0  # Size of each cell in degrees

    # Function to create a rectangle centered on a point
    def create_rectangle(lng, lat):
        return ee.Geometry.Rectangle([lng - 0.5, lat - 0.5, lng + 0.5, lat + 0.5])

    # Generate the grid
    grid_polygons = []
    lat = min_lat
    while lat <= max_lat:
        lng = min_lng
        while lng <= max_lng:
            rectangle = create_rectangle(lng, lat)
            grid_polygons.append(rectangle)
            lng += cell_size
        lat += cell_size

    # Create a FeatureCollection from the grid
    grid_fc = ee.FeatureCollection(grid_polygons)
    
    # Filter to include polygons that intersect the accurate US geometry
    filtered_grid = grid_fc.map(lambda feature: feature.set('intersects', us_geometry.intersects(feature.geometry()))).filter(ee.Filter.eq('intersects', True))
    
    # Fetch filtered polygons as a list of dictionaries
    filtered_grid_infos = filtered_grid.getInfo()  # Fetch information for local use

    file_path = "config/US_polygons.json"
    # Write intersecting polygons to a JSON file
    with open(file_path, 'w') as f:
        json.dump(filtered_grid_infos, f)

    # Log the result
    total_polygons = filtered_grid.size().getInfo()
    print(f"Successfully saved the US sub-region polygons to {file_path}")
    print(f"Total polygons intersecting with US geometry: {total_polygons}")



