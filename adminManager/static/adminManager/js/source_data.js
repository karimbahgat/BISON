
/////////////
// main country map

// style
var fill = new ol.style.Fill({
    color: 'rgb(6,75,52)'
});
var lineColor = 'rgba(255, 0, 0, 0.8)'; //'rgb(29,107,191)';
var lineStrokes = [
    new ol.style.Stroke({
        color: lineColor,
        width: 3,
    }),
    new ol.style.Stroke({
        color: lineColor,
        width: 2,
        lineDash: [3,9]
    }),
    new ol.style.Stroke({
        color: lineColor,
        width: 1.5,
        lineDash: [5,5]
    }),
    new ol.style.Stroke({
        color: lineColor,
        width: 1,
        lineDash: [5,5]
    }),
    new ol.style.Stroke({
        color: lineColor,
        width: 0.5,
        lineDash: [5,5]
    }),
];


// labelling
var labelStyle = new ol.style.Style({
    geometry: function(feature) {
        // create a geometry that defines where the label will be display
        var geom = feature.getGeometry();
        if (geom.getType() == 'Polygon') {
            // polygon
            // place label at the bbox/center of the polygon
            var extent = feature.getGeometry().getExtent();
            var newGeom = ol.geom.Polygon.fromExtent(extent);
        } else {
            // multi polygon
            // place label at the bbox/center of the largest polygon
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

// layer
function getStyle(feature) {
    //var labelStyle = resultLabelStyle.clone();
    //label = `${feature.getId()}: ${feature.get('displayName')}`;
    //labelStyle.getText().setText(label);
    level = feature.get('level');
    console.log(level)
    style = new ol.style.Style({
        fill: null,
        stroke: lineStrokes[level],
    });
    return [style]; //,labelStyle];
}
var layer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: getStyle,
});

// map
var map = new ol.Map({
    target: 'map',
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
        layer
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([0,0]),
        zoom: 1
    })
});

/*
map.on('pointermove', function(evt) {
    // get feat at pointer
    let cursorFeat = null;
    map.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
        cursorFeat = feature;
    });
    // if any feat was found
    if (cursorFeat != null) {
        // clear any existing feature text
        resultLayer.getSource().forEachFeature(function (feature) {
            feature.setStyle([resultStyle]);
        });
        // update the text style for the found feature
        var label = cursorFeat.get('displayName');
        var labelStyle = resultLabelStyle.clone();
        labelStyle.getText().setText(label);
        cursorFeat.setStyle([resultStyle,labelStyle]);
    } else {
        // clear any existing feature text
        resultLayer.getSource().forEachFeature(function (feature) {
            feature.setStyle([resultStyle]);
        });
    };
});
*/

function onMoveEnd() {
    fetchAdmins(source);
}

function getMapBounds() {
    extent = map.getView().calculateExtent();
    return ol.proj.transformExtent(extent, 'EPSG:3857','EPSG:4326');
}

function getAdminIds() {
    ids = [];
    layer.getSource().forEachFeature(function (feat) {
        ids.push(feat.get('id'));
    });
    return ids;
}

function fetchAdmins(source_id) {
    if (fetching) {
        // already fetching
        return
    } else {
        fetching = true;
        document.getElementById('map-loading').style.visibility = 'visible';
    };

    [minx, miny, maxx, maxy] = getMapBounds();
    //currentAdminIds = getAdminIds();
    urlParams = new URLSearchParams();
    urlParams.set('source', source_id);
    //urlParams.set('exclude', currentAdminIds.join(','));
    if (firstFetch) {
        urlParams.set('summary_only', 'true');
        urlParams.set('geom', 'false');
    } else {
        urlParams.set('xmin', minx);
        urlParams.set('ymin', miny);
        urlParams.set('xmax', maxx);
        urlParams.set('ymax', maxy);
        urlParams.set('minimum_extent_fraction', 30);
    };
    url = '/api/admins?' + urlParams.toString();
    console.log(url);
    fetch(url).then(resp=>resp.json()).then(data=>receiveAdmins(data));
}

function receiveAdmins(data) {
    console.log(data)
    setLayerData(data);
    if (firstFetch) {
        if (data.bbox) {
            zoomMapToBbox(data.bbox);
        };
        firstFetch = false;
    };
    // open for new fetches
    fetching = false;
    document.getElementById('map-loading').style.visibility = 'hidden';
}

function setLayerData(data) {
    src = layer.getSource();
    // clear existing layer
    src.clear();
    // add to layer
    wktReader = new ol.format.WKT();
    for (info of data.result) {
        geom = wktReader.readGeometry(info.wkt, {dataProjection:'EPSG:4326', featureProjection:'EPSG:3857'});
        delete info.wkt;
        info.geometry = geom;
        feat = new ol.Feature(info);
        src.addFeature(feat);
    };
}

function zoomMapToLayer(lyr) {
    map.getView().fit(lyr.getSource().getExtent());
    map.getView().setZoom(map.getView().getZoom()-0.5);
}

function zoomMapToBbox(bbox) {
    bbox = ol.proj.transformExtent(bbox, 'EPSG:4326', 'EPSG:3857');
    map.getView().fit(bbox);
    map.getView().setZoom(map.getView().getZoom()-0.5);
}

// fetch admins when map has moved

map.on('moveend', onMoveEnd);
