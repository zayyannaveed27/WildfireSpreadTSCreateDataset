'''
GeoTIFF Image Processor and Visualizer

This script processes the multi-channel GeoTIFF image file and performs the following tasks:

1. Reads and validates the image to ensure it contains 22 channels.
2. Extracts and prints metadata such as image dimensions, bounds, CRS, and transform.
3. Reads each channel and maps it to a predefined list of channel names.
4. Prints the shape and data type of each channel.
5. Counts the number of active fire pixels in the "VIIRS band M11" channel.
6. Creates an RGB composite image using "VIIRS band M11" (R), "VIIRS band I2" (G), and "VIIRS band I1" (B).
7. Displays the RGB composite image with geographic coordinates.

Usage:
    python script_name.py <path_to_geotiff_image>
'''

import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
import numpy as np
import argparse

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process and visualize a multi-channel GeoTIFF image.")
    parser.add_argument("image_filepath", help="Path to the GeoTIFF image file.")
    return parser.parse_args()

def load_tiff_metadata(image_file):
    """Load GeoTIFF metadata and channels."""
    channel_names = [
        "VIIRS band M11", "VIIRS band I2", "VIIRS band I1", "NDVI", "EVI2", 
        "Total precipitation", "Wind speed", "Wind direction", 
        "Minimum temperature", "Maximum temperature", "Energy release component", 
        "Specific humidity", "Slope", "Aspect", "Elevation", 
        "Palmer drought severity index", "Landcover class", 
        "Forecast total precipitation", "Forecast wind speed", 
        "Forecast wind direction", "Forecast temperature", 
        "Forecast specific humidity"
    ]

    with rasterio.open(image_file) as tif_image:
        assert tif_image.count == 22, f"Expected 22 channels, but found {tif_image.count}"
        print(f"Image width: {tif_image.width}")
        print(f"Image height: {tif_image.height}")
        print(f"Image bounds: {tif_image.bounds}")
        print(f"Image CRS: {tif_image.crs}")
        print(f"Image transform: {tif_image.transform}")

        channels_data = {}
        for i in range(1, tif_image.count + 1):
            channels_data[channel_names[i-1]] = tif_image.read(i)

        return tif_image.crs, tif_image.transform, tif_image.bounds, channels_data

def summarize_channels(channels_data):
    """Print a summary of the channels."""
    for name, data in channels_data.items():
        print(f"{name}: Shape = {data.shape}, Data Type = {data.dtype}")
        if name == "VIIRS band M11":
            num_fire_pixels = np.count_nonzero(data)
            print(f"Number of active fire pixels in {name}: {num_fire_pixels}")

def create_rgb_image(channels_data):
    """Create an RGB composite image from selected bands."""
    red = channels_data["VIIRS band M11"]
    green = channels_data["VIIRS band I2"]
    blue = channels_data["VIIRS band I1"]

    rgb_image = np.stack([red, green, blue], axis=-1)
    rgb_image = (rgb_image - rgb_image.min()) / (rgb_image.max() - rgb_image.min())
    return rgb_image

def plot_rgb_image(rgb_image, transform):
    """Plot the RGB composite image."""
    height, width = rgb_image.shape[:2]
    x_coords = np.arange(width) * transform[0] + transform[2]
    y_coords = np.arange(height) * transform[4] + transform[5]

    plt.figure(figsize=(10, 8))
    plt.imshow(rgb_image, extent=(x_coords[0], x_coords[-1], y_coords[-1], y_coords[0]))
    plt.title('RGB Composite (VIIRS band M11, I2, I1)')
    plt.xlabel('Easting (m)')
    plt.ylabel('Northing (m)')
    plt.colorbar(label='Intensity')
    plt.axis('on')
    plt.show()

if __name__ == "__main__":
    args = parse_arguments()

    # Load metadata and channels
    crs, transform, bounds, channels_data = load_tiff_metadata(args.image_filepath)

    # Create and plot RGB image
    rgb_image = create_rgb_image(channels_data)
    plot_rgb_image(rgb_image, transform)
