# -*- coding: utf-8 -*-

"""Aggregate the number of inhabitants for a regions/polygons within Germany.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import zipfile
import shutil
import glob
import logging

# External libraries
import pandas as pd
import geopandas as gpd

# oemof libraries
import oemof.tools.logger

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries
import reegis_tools.tools as tools


def get_ew_shp_file(year):
    if year < 2011:
        logging.error("Shapefile with inhabitants are available since 2011.")
        logging.error("Try to find another source to get older data sets.")
        raise AttributeError('Years < 2011 are not allowed in this function.')

    outshp = os.path.join(cfg.get('paths', 'inhabitants'),
                          'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(outshp):
        url = cfg.get('inhabitants', 'url_geodata_ew').format(year=year,
                                                              var1='{0}')
        filename_zip = os.path.join(cfg.get('paths', 'inhabitants'),
                                    cfg.get('inhabitants', 'vg250_ew_zip'))
        msg = tools.download_file(filename_zip, url.format('ebene'))
        if msg == 404:
            logging.warning("Wrong URL. Try again with different URL.")
            tools.download_file(
                filename_zip, url.format('ebenen'), overwrite=True)

        zip_ref = zipfile.ZipFile(filename_zip, 'r')
        zip_ref.extractall(cfg.get('paths', 'inhabitants'))
        zip_ref.close()
        subs = next(os.walk(cfg.get('paths', 'inhabitants')))[1]
        mysub = None
        for sub in subs:
            if 'vg250' in sub:
                mysub = sub
        pattern_path = list()

        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'VG250_VWG*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'vg250_vwg*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250_ebenen-historisch',
                                         'de{0}12'.format(str(year)[-2:]),
                                         'vg250_vwg*'))

        for pa_path in pattern_path:
            for file in glob.glob(pa_path):
                file_new = os.path.join(cfg.get('paths', 'inhabitants'),
                                        'VG250_VWG_' + str(year) + file[-4:])
                shutil.copyfile(file, file_new)

        shutil.rmtree(os.path.join(cfg.get('paths', 'inhabitants'), mysub))

        os.remove(filename_zip)


def get_ew_geometry(year):
    filename_shp = os.path.join(cfg.get('paths', 'inhabitants'),
                                'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(filename_shp):
        get_ew_shp_file(year)

    vwg = reegis_tools.geometries.Geometry()
    vwg.gdf = gpd.read_file(filename_shp)

    # replace polygon geometry by its centroid
    vwg.gdf['geometry'] = vwg.gdf.representative_point()

    return vwg


def get_ew_by_region(year, geo, col=None):
    if col is None:
        col = geo.name
    ew = get_ew_geometry(year)
    ew.gdf = reegis_tools.geometries.spatial_join_with_buffer(
        ew, geo)
    return ew.gdf.groupby(col).sum()['EWZ']


def get_ew_by_federal_states(year):
    geo = reegis_tools.geometries.Geometry(name='federal_state')
    geo.load(cfg.get('paths', 'geometry'),
             cfg.get('geometry', 'federalstates_polygon'))
    return get_ew_by_region(year, geo)


if __name__ == "__main__":
    oemof.tools.logger.define_logging()
    spatial_file_fs = os.path.join(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    spatial_dfs = pd.read_csv(spatial_file_fs, index_col='gen')
    print(get_ew_by_federal_states(2015))
