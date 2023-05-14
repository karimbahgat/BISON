
/////////////
// main map
function getLargestPolyExtent(geom) {
    if (geom.getType() == 'Polygon') {
        // polygon
        // get bbox of the polygon
        var extent = geom.getExtent();
        var newGeom = ol.geom.Polygon.fromExtent(extent);
    } else {
        // multi polygon
        // get bbox of the largest polygon
        var largestGeom = null;
        var largestArea = null;
        for (poly of geom.getPolygons()) {
            var extent = poly.getExtent();
            var extentGeom = ol.geom.Polygon.fromExtent(extent);
            var extentArea = extentGeom.getArea();
            if (extentArea > largestArea) {
                largestGeom = extentGeom;
                largestArea = extentArea;
            };
        };
        var newGeom = largestGeom;
    };
    return newGeom;
};
function getFeatureCentroid(feature) {
    geom = feature.getGeometry();
    extent = geom.getExtent(); //getLargestPolyExtent(geom);
    center = new ol.geom.Point(ol.extent.getCenter(extent));
    return center;
}

// disambiguation style
var disambiguationStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(220, 220, 255, 0.3)',
    }),
    stroke: new ol.style.Stroke({
        color: 'rgb(29,107,191)', //'rgb(49, 127, 211)',
        width: 2.5,
    }),
});
var disambiguationPointStyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 10,
        fill: new ol.style.Fill({
          color: 'rgb(29,107,191)',
        }),
    }),
    geometry: getFeatureCentroid
});

// basket style
var basketStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(240, 178, 35, 0.3)', 
    }),
    stroke: new ol.style.Stroke({
        color: 'rgb(240, 178, 35)', 
        width: 2.5,
    }),
});
var basketPointStyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 10,
        fill: new ol.style.Fill({
          color: 'rgb(240, 178, 35)',
        }),
    }),
    geometry: getFeatureCentroid
});

// selected style
var selectedStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(255, 255, 255, 0)', // fully transparent
    }),
    stroke: new ol.style.Stroke({
        color: 'rgb(0, 240, 252)', //'rgb(49, 127, 211)',
        width: 2.5,
    }),
});
var selectedPointStyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 10,
        fill: new ol.style.Fill({
          color: 'rgb(0, 240, 252)',
        }),
    }),
    geometry: getFeatureCentroid
});

// similar style
var similarStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(255, 255, 255, 0)', // fully transparent
    }),
    stroke: new ol.style.Stroke({
        color: 'rgb(255, 0, 0)',
        width: 2.5,
        lineDash: [10,10]
    }),
});
var similarPointStyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 10,
        fill: new ol.style.Fill({
            color: 'rgb(255, 0, 0)',
        }),
    }),
    geometry: getFeatureCentroid
});


// layers
var disambiguationLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: [disambiguationStyle, disambiguationPointStyle],
});

var basketLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: [basketStyle, basketPointStyle],
});

var selectedLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: [selectedStyle, selectedPointStyle],
});

var similarLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: [similarStyle, similarPointStyle],
});

// labelling
/*
var disambiguationLabelStyle = new ol.style.Style({
    geometry: function(feature) {
        // create a geometry that defines where the label will be display
        var geom = feature.getGeometry();
        var newGeom = getLargestPoly(geom);
        return newGeom;
    },
    text: new ol.style.Text({
        //font: '12px Calibri,sans-serif',
        fill: new ol.style.Fill({ color: '#000' }),
        stroke: new ol.style.Stroke({
            color: '#fff', width: 2
        }),
        overflow: true,
    }),
});
*/

// map
var disambiguationMap = new ol.Map({
    target: 'disambiguation-map',
    controls: ol.control.defaults().extend([new ol.control.FullScreen(),
                                            new ol.control.ScaleLine({units: 'metric'}),
                                            ]),
    layers: [
    new ol.layer.Tile({
        source: new ol.source.XYZ({
            attributions: 'Satellite Imagery from Google',
            url:
            'http://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}',
            maxZoom: 20,
            crossOrigin: 'anonymous' // necessary for converting map to img during pdf generation: https://stackoverflow.com/questions/66671183/how-to-export-map-image-in-openlayer-6-without-cors-problems-tainted-canvas-iss
        })}),
        basketLayer,
        disambiguationLayer,
        similarLayer,
        selectedLayer
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([0,0]),
        zoom: 1
    })
});

/*
disambiguationMap.on('pointermove', function(evt) {
    // get feat at pointer
    let cursorFeat = null;
    disambiguationMap.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
        cursorFeat = feature;
    });
    // if any feat was found
    if (cursorFeat != null) {
        // clear any existing feature text
        disambiguationLayer.getSource().forEachFeature(function (feature) {
            feature.setStyle([disambiguationStyle]);
        });
        // update the text style for the found feature
        var label = cursorFeat.get('displayName');
        var labelStyle = disambiguationLabelStyle.clone();
        labelStyle.getText().setText(label);
        cursorFeat.setStyle([disambiguationStyle,labelStyle]);
    } else {
        // clear any existing feature text
        disambiguationLayer.getSource().forEachFeature(function (feature) {
            feature.setStyle([disambiguationStyle]);
        });
    };
});
*/

disambiguationMap.on('click', function(evt) {
    // get feat at pointer
    let cursorFeat = null;
    disambiguationMap.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
        cursorFeat = feature;
    });
    // if any feat was found
    if (cursorFeat != null) {
        selectGeom(cursorFeat.getId());
    };
});

function addGeomToDisambiguationMap(geomData) {
    props = {'id': geomData.id,
            'displayName': getDisplayName(geomData)
            };
    feat = {'type': 'Feature',
            'id': geomData.id,
            'properties': props,
            'geometry': geomData['geom']};
    feat = new ol.format.GeoJSON().readFeature(feat, {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
    disambiguationLayer.getSource().addFeature(feat);
    //disambiguationMap.getView().fit(disambiguationLayer.getSource().getExtent());
    //disambiguationMap.getView().setZoom(disambiguationMap.getView().getZoom()-1);
    // add to selected layer
    /*
    if (geomData.id == currentSelectedGeomId) {
        selectMapGeom(geomData.id);
    };
    */
};

function zoomToDisambiguationLayer() {
    extent = disambiguationLayer.getSource().getExtent();
    paddedZoomToExtent(extent);
}

function zoomToSelectedLayer() {
    extent = selectedLayer.getSource().getExtent();
    paddedZoomToExtent(extent);
}

function zoomToBasketLayer() {
    extent = basketLayer.getSource().getExtent();
    paddedZoomToExtent(extent);
}

function zoomToDisambiguationId(adminId) {
    feat = disambiguationLayer.getSource().getFeatureById(adminId);
    extent = feat.getGeometry().getExtent();
    paddedZoomToExtent(extent);
}

function paddedExtent(extent, padding=0.1) {
    // add normal percent padding (doesnt consider left-right side of map)
    extent = extent.slice(); // to avoid modifying original extent
    // pad around extent
    extentWidth = extent[2] - extent[0];
    pad = extentWidth * padding;
    extent = ol.extent.buffer(extent, pad, extent);
    return extent;
}

function paddedZoomToExtent(extent, padding=0.1, animated=false) {
    // adds padding to ensure the extent is centered on right side of map
    extent = extent.slice(); // to avoid modifying original extent
    // pad around extent
    extentWidth = extent[2] - extent[0];
    pad = extentWidth * padding;
    extent = ol.extent.buffer(extent, pad, extent);
    // offset extent to the left so geom shows on the right
    offsetFactor = 1;
    offsetLeft = extentWidth * offsetFactor;
    extent[0] = extent[0] - offsetLeft;
    // perform zoom
    opts = {};
    if (animated) {
        opts['duration'] = 1000;
    };
    disambiguationMap.getView().fit(extent, opts);
}

function getPaddedMapExtent() {
    extent = disambiguationMap.getView().calculateExtent();
    extent = extent.slice();
    // ignore leftmost half
    w = extent[2] - extent[0];
    extent[0] = extent[0] + (w/2.0)
    return extent;
}

function selectMapGeom(adminId) {
    selectedLayer.getSource().clear();
    fromFeat = disambiguationLayer.getSource().getFeatureById(adminId);
    props = fromFeat.getProperties();
    feat = new ol.Feature(props);
    feat.setGeometry(fromFeat.getGeometry());
    selectedLayer.getSource().addFeature(feat);
    // make sure selected geom is within current extent
    curExtent = getPaddedMapExtent();
    geomExtent = feat.getGeometry().getExtent();
    geomExtent = paddedExtent(geomExtent);
    extent = ol.extent.extend(curExtent, geomExtent);
    paddedZoomToExtent(extent, padding=0);
}

function addToBasketGeoms(adminId) {
    fromFeat = disambiguationLayer.getSource().getFeatureById(adminId);
    props = fromFeat.getProperties();
    feat = new ol.Feature(props);
    feat.setGeometry(fromFeat.getGeometry());
    feat.setId(fromFeat.getId())
    basketLayer.getSource().addFeature(feat);
    // make sure selected geom is within current extent
    curExtent = getPaddedMapExtent();
    geomExtent = feat.getGeometry().getExtent();
    geomExtent = paddedExtent(geomExtent);
    extent = ol.extent.extend(curExtent, geomExtent);
    paddedZoomToExtent(extent, padding=0);
}

function removeFromBasketGeoms(adminId) {
    feat = basketLayer.getSource().getFeatureById(adminId);
    basketLayer.getSource().removeFeature(feat);
}

function addSimilarGeomsToMap(entries) {
    // first clear
    //similarLayer.getSource().clear();
    // then add
    for (geomData of entries) {
        props = {'id': geomData.id,
            'displayName': getDisplayName(geomData)
        };
        feat = {'type': 'Feature',
            'id': geomData.id,
            'properties': props,
            'geometry': geomData['geom']};
        feat = new ol.format.GeoJSON().readFeature(feat, {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
        similarLayer.getSource().addFeature(feat);
    };
}

////////////////

function onMoveEnd() {
    fetchAdmins();
}

function getMapBounds() {
    extent = disambiguationMap.getView().calculateExtent();
    return ol.proj.transformExtent(extent, 'EPSG:3857','EPSG:4326');
}

function getAdminIds() {
    ids = [];
    disambiguationLayer.getSource().forEachFeature(function (feat) {
        ids.push(feat.get('id'));
    });
    return ids;
}

function fetchAdmins() {
    adminIds = getAdminIds();
    if (adminIds.length == 0) {
        return;
    };

    // indicate fetching start
    fetchingTime = Date.now();
    document.getElementById('map-loading').style.visibility = 'visible';

    [minx, miny, maxx, maxy] = getMapBounds();
    urlParams = new URLSearchParams();
    urlParams.set('ids', adminIds.join(','));
    urlParams.set('xmin', minx);
    urlParams.set('ymin', miny);
    urlParams.set('xmax', maxx);
    urlParams.set('ymax', maxy);
    urlParams.set('geom_size_limit', 100000*1000);
    urlParams.set('minimum_extent_fraction', 30);
    url = '/api/admins?' + urlParams.toString();
    console.log(url);
    let requested = fetchingTime; // pass along the requested timestamp
    fetch(url).then(resp=>resp.json()).then(data=>receiveAdmins(requested, data));
}

function receiveAdmins(requested, data) {
    console.log(data)
    // update map geoms
    updateLayerGeometry(data);
    // stop loading icon if no newer requests have been made
    if (requested == fetchingTime) {
        document.getElementById('map-loading').style.visibility = 'hidden';
    };
}

function updateLayerGeometry(data) {
    src = disambiguationLayer.getSource();
    // add to layer
    wktReader = new ol.format.WKT();
    for (info of data.result) {
        id = info.id;
        feat = src.getFeatureById(id);
        geom = wktReader.readGeometry(info.wkt, {dataProjection:'EPSG:4326', featureProjection:'EPSG:3857'});
        feat.setGeometry(geom);
    };
}

// fetch admins when map has moved
fetchingTime = null;
disambiguationMap.on('moveend', onMoveEnd);

// hacky fix to disable map loading animation on startup
// has to be visible on startup to be visible later
setTimeout(function() {
    document.getElementById('map-loading').style.visibility = 'hidden';
}, 10)

