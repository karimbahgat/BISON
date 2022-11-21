
_geod = None

def get_pyproj_geod():
    global _geod
    if _geod is None:
        # only create the geod once in case of overhead
        from pyproj import Geod
        _geod = Geod(ellps="WGS84")
    return _geod

def geojson_area_perimeter(geoj):
    # area may be negative if incorrect orientation
    # but the abs(area) will be correct as long as ext and holes
    # have opposite orientation
    import numpy as np
    geod = get_pyproj_geod()
    
    if geoj['type'] == 'MultiPolygon':
        polys = geoj['coordinates']
    elif geoj['type'] == 'Polygon':
        polys = [geoj['coordinates']]
        
    area = 0
    perim = 0
    for poly in polys:
        for ring in poly:
            coords = np.array(ring)
            lons,lats = coords[:,0],coords[:,1]
            _area,_perim = geod.polygon_area_perimeter(lons, lats)
            area += _area
            perim += _perim
    return area, perim

def calc_stats(feats):
    stats = {}
    # unit count
    stats['boundaryCount'] = len(feats)
    # vertices, area, and perimiter
    #from shapely.geometry import shape
    area = 0
    perim = 0
    verts = 0
    for feat in feats:
        # geodesy

        # pyproj
        # pyproj shapely version
        #geom = shape(feat['geometry'])
        #geod = get_pyproj_geod()
        #_area, _perim = geod.geometry_area_perimeter(geom)
        # pyproj geojson version, much faster
        _area, _perim = geojson_area_perimeter(feat['geometry'])

        # some faster alternatives that avoids pyproj? 
        # https://stackoverflow.com/questions/6656475/python-speeding-up-geographic-comparison
        # https://github.com/geospace-code/pymap3d
        # https://github.com/actushumanus/nphaversine
        # https://github.com/qyliu-hkust/fasthaversine
        # https://github.com/yandex/mapsapi-area
        # https://github.com/Turfjs/turf/blob/master/packages/turf-area/index.ts

        area += _area
        perim += _perim
        
        # verts
        _verts = 0
        if feat['geometry']['type'] == 'MultiPolygon':
            polys = feat['geometry']['coordinates']
        elif feat['geometry']['type'] == 'Polygon':
            polys = [feat['geometry']['coordinates']]
        for poly in polys:
            for ring in poly:
                _verts += len(ring)
        verts += _verts
    area = abs(area) / 1000000 # convert m2 to km2 + fix pyproj which treats ccw as positive area (opposite of geojson)
    perim = perim / 1000 # convert m to km
    stats['statsArea'] = area
    stats['statsPerimeter'] = perim
    stats['statsVertices'] = verts
    # line resolution
    stats['statsLineResolution'] = (perim * 1000) / verts # meters between vertices
    stats['statsVertexDensity'] = verts / perim # vertices per km
    return stats
