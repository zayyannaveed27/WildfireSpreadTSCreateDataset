import datetime
import os
import urllib
from glob import glob
from pprint import pprint

import cv2
import ee
import imageio
import numpy as np
import tensorflow as tf
import yaml
from google.cloud import storage
from matplotlib import pyplot as plt

from .satellites.FIRM import FIRMS
from .satellites.FirePred import FirePred
from .satellites.GOES import GOES
from .satellites.GOES_FIRE import GOES_FIRE
from .satellites.Landsat8 import Landsat8
from .satellites.MODIS import MODIS
from .satellites.Sentinel1 import Sentinel1
from .satellites.Sentinel2 import Sentinel2
from .satellites.VIIRS import VIIRS
from .satellites.VIIRS_Day import VIIRS_Day
from .utils.EarthEngineMapClient import EarthEngineMapClient
from Preprocessing.PreprocessingService import PreprocessingService


class DatasetPrepareService:
    def __init__(self, location, roi=None, config=None):
        self.config = config
        self.location = location
        self.rectangular_size = self.config.get('rectangular_size')
        self.latitude = self.config.get(self.location).get('latitude')
        self.longitude = self.config.get(self.location).get('longitude')
        self.start_time = self.config.get(location).get('start')
        self.end_time = self.config.get(location).get('end')

        self.rectangular_size = self.config.get('rectangular_size')
        if roi == None:
            self.geometry = ee.Geometry.Rectangle(
                [self.longitude - self.rectangular_size, self.latitude - self.rectangular_size,
                 self.longitude + self.rectangular_size, self.latitude + self.rectangular_size])
        else:
            self.geometry = ee.Geometry.Rectangle(roi)

        self.scale_dict = {"VIIRS_Day": 375, "GOES": 375, "GOES_FIRE": 2000, "FIRMS": 500, "Sentinel2": 20,
                           "VIIRS": 375, "MODIS": 500, "Sentinel1_asc": 20, "Sentinel1_dsc": 20, "FirePred": 375}

    def cast_to_uint8(self, image):
        return image.multiply(512).uint8()

    def get_satellite_client(self, satellite):
        if satellite == 'Sentinel2':
            satellite_client = Sentinel2(False)
        elif satellite == 'MODIS':
            satellite_client = MODIS()
        elif satellite == 'GOES':
            satellite_client = GOES()
        elif satellite == 'Sentinel1_asc':
            satellite_client = Sentinel1("asc", self.location)
        elif satellite == 'Sentinel1_dsc':
            satellite_client = Sentinel1("dsc", self.location)
        elif satellite == 'VIIRS':
            satellite_client = VIIRS()
        elif satellite == 'FIRMS':
            satellite_client = FIRMS()
        elif satellite == 'GOES_FIRE':
            satellite_client = GOES_FIRE()
        elif satellite == 'VIIRS_Day':
            satellite_client = VIIRS_Day()
        elif satellite == 'FirePred':
            satellite_client = FirePred()
        else:
            satellite_client = Landsat8()
        return satellite_client

    def prepare_daily_image(self, enable_image_downloading, satellite, date_of_interest, time_stamp_start="00:00",
                            time_stamp_end="23:59"):
        satellite_client = self.get_satellite_client(satellite)
        img_collection = satellite_client.collection_of_interest(date_of_interest + 'T' + time_stamp_start,
                                                                 date_of_interest + 'T' + time_stamp_end,
                                                                 self.geometry)
        vis_params = satellite_client.get_visualization_parameter()
        img_collection_as_gif = img_collection.select(vis_params.get('bands')).map(self.cast_to_uint8)
        if enable_image_downloading and len(img_collection.max().getInfo().get('bands')) != 0:
            vis_params['format'] = 'jpg'
            vis_params['dimensions'] = 768
            url = img_collection.max().clip(self.geometry).getThumbURL(vis_params)
            print(url)
            urllib.request.urlretrieve(url, 'images_for_gif/' + self.location + '/' + satellite + str(
                date_of_interest) + '.jpg')
        return img_collection, img_collection_as_gif

    def download_image_to_gcloud(self, img_coll, satellite, index, utm_zone):
        '''
        Export images to google cloud, the output image is a rectangular with the center at given latitude and longitude
        :param img: Image in GEE
        :return: None
        '''

        # Setup the task.
        # size = img_coll.size().getInfo()
        # img_coll = img_coll.toList(size)
        # for i in range(size):
        # img = ee.Image(img_coll.get(i))
        if satellite != 'GOES_every':
            if "year" in self.config:
                filename = "WildfireSpreadTS/" + str(self.config["year"]) + '/' + self.location + '/' + index
            else:
                filename = self.location + '/' + satellite + '/' + index
            img = img_coll.max().toFloat()
            image_task = ee.batch.Export.image.toCloudStorage(
                image=img,
                description='Image Export',
                fileNamePrefix=filename,
                bucket=self.config.get('output_bucket'),
                scale=self.scale_dict.get(satellite),
                crs='EPSG:' + utm_zone,
                maxPixels=1e13,
                # fileDimensions=256,
                # fileFormat='TFRecord',
                region=self.geometry.toGeoJSON()['coordinates'],
            )
            image_task.start()
            print('Start with image task (id: {}).'.format(image_task.id))
        else:
            size = img_coll.size().getInfo()
            img_list = img_coll.toList(size)

            n = 0
            while n < size:
                img = ee.Image(img_list.get(n))

                image_task = ee.batch.Export.image.toCloudStorage(image=img.toFloat(),
                                                                  description='Image Export',
                                                                  fileNamePrefix=self.location + satellite + '/' + "Cal_fire_" + self.location + satellite + '-' + index + '-' + str(
                                                                      n),
                                                                  bucket=self.config.get('output_bucket'),
                                                                  scale=self.scale_dict.get(satellite),
                                                                  crs='EPSG:32610',
                                                                  maxPixels=1e13,
                                                                  # fileDimensions=256,
                                                                  # fileFormat='TFRecord',
                                                                  region=self.geometry.toGeoJSON()['coordinates']
                                                                  )
                image_task.start()
                print('Start with image task (id: {}).'.format(image_task.id) + index)
                n += 1

    def download_dataset_to_gcloud(self, satellites, utm_zone, download_images_as_jpeg_locally, n_buffer_days=0):
        '''

        :param satellites:
        :param utm_zone:
        :param download_images_as_jpeg_locally:
        :param n_buffer_days: Number of days before and after the fire dates for which we also want to collect data.
        :return:
        '''
        filenames = []
        buffer_days = datetime.timedelta(days=n_buffer_days)
        time_dif = self.end_time - self.start_time + 2 * buffer_days + datetime.timedelta(days=1)

        for i in range(time_dif.days):
            date_of_interest = str(self.start_time - buffer_days + datetime.timedelta(days=i))

            for satellite in satellites:
                img_collection, img_collection_as_gif = self.prepare_daily_image(download_images_as_jpeg_locally,
                                                                                 satellite=satellite,
                                                                                 date_of_interest=date_of_interest)
                n_images = len(img_collection.getInfo().get("features"))
                if n_images > 1:
                    raise RuntimeError(f"Found {n_images} features in img_collection returned by prepare_daily_image. "
                                       f"Should have been exactly 1.")
                max_img = img_collection.max()
                if len(max_img.getInfo().get('bands')) != 0:
                    self.download_image_to_gcloud(img_collection, satellite, date_of_interest, utm_zone)
        if download_images_as_jpeg_locally:
            images = []
            for filename in filenames:
                images.append(imageio.imread('images_for_gif/' + self.location + '/' + filename + '.jpg'))
            imageio.mimsave('images_for_gif/' + self.location + '.gif', images, format='GIF', fps=1)

    def download_blob(self, bucket_name, prefix, destination_file_name):
        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        for blob in blobs:
            filename = blob.name.split('/')[2].replace('.tif', '') + '_' + blob.name.split('/')[1] + '.tif'
            blob.download_to_filename(destination_file_name + filename)
            print(
                "Blob {} downloaded to {}.".format(
                    filename, destination_file_name
                )
            )

    def batch_downloading_from_gclound_training(self, satellites):
        for satellite in satellites:
            if "year" in self.config:
                blob_name = str(self.config["year"]) + '/' + self.location + '/'
                destination_name = 'data/' + str(self.config["year"]) + '/' + self.location + '/'
            else:
                blob_name = self.location + '/' + satellite + '/'
                destination_name = 'data/' + self.location + '/' + satellite + '/'
            dir_name = os.path.dirname(destination_name)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            self.download_blob(self.config.get('output_bucket'), blob_name, destination_name)
