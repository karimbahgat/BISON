
/////////////
// main country map

// style
var resultStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgb(6,75,52)'
    }),
    stroke: new ol.style.Stroke({
        color: 'white',
        width: 0.5,
    }),
});

// labelling
var resultLabelStyle = new ol.style.Style({
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
    return [resultStyle]; //,labelStyle];
}
var resultLayer = new ol.layer.Vector({
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
        resultLayer
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

function addResultToMap(searchId2, matchData) {
    props = {'geomId': matchData.id,
            'displayName': getDisplayName(matchData)
            };
    feat = {'type': 'Feature',
            'id': searchId2,
            'properties': props,
            'geometry': matchData['geom']};
    feat = new ol.format.GeoJSON().readFeature(feat, {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});

    existingFeat = resultLayer.getSource().getFeatureById(searchId2);
    if (existingFeat != null) {
        // update existing feat
        existingFeat.setGeometry(feat.getGeometry());
        existingFeat.setProperties(feat.getProperties());
        map.getView().fit(feat.getGeometry().getExtent());
        map.getView().setZoom(map.getView().getZoom()-1);
    } else {
        // add new feat
        resultLayer.getSource().addFeature(feat);
        map.getView().fit(feat.getGeometry().getExtent());
        map.getView().setZoom(map.getView().getZoom()-1);
    }
};

function zoomMapToSearchId(searchId2) {
    feat = resultLayer.getSource().getFeatureById(searchId2);
    map.getView().fit(feat.getGeometry().getExtent());
    map.getView().setZoom(map.getView().getZoom()-1);
}

function removeResultFromMap(searchId2, matchData) {
    feat = resultLayer.getSource().getFeatureById(searchId2);
    resultLayer.getSource().removeFeature(feat);
}

function zoomMapToAllResults() {
    map.getView().fit(resultLayer.getSource().getExtent());
    map.getView().setZoom(map.getView().getZoom()-0.5);
}

