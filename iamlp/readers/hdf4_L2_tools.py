import gdal
from gdalconst import GA_ReadOnly

from iamlp.settings import delayed


def load_hdf4(f):
    handle = gdal.Open(f, GA_ReadOnly)
    ds = handle.GetSubDatasets()
    meta = handle.GetMetadata()
    return handle, ds, meta

directions = ('North', 'South', 'East', 'West')
def get_subdataset_bounds(meta):
    from iamlp.selection.geo_selection import SpatialBounds
    bounds = SpatialBounds(*tuple(float(meta['{}BoundingCoord'.format(word)])
                                  for word in directions))
    time = meta['StartTime']
    return bounds, time