
/////////////
// main country map

// layer
var disambiguationStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(255, 255, 255, 0)', // fully transparent
    }),
    stroke: new ol.style.Stroke({
        color: 'rgba(255, 0, 0, 0.8)',
        width: 1.5,
        lineDash: [10,10]
    }),
});
var selectedStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(220, 220, 255, 0.3)',
    }),
    stroke: new ol.style.Stroke({
        color: 'rgb(29,107,191)', //'rgb(49, 127, 211)',
        width: 2.5,
    }),
});

var disambiguationLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: disambiguationStyle,
});

var selectedLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: selectedStyle,
});

// labelling
var disambiguationLabelStyle = new ol.style.Style({
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
        disambiguationLayer,
        selectedLayer
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([0,0]),
        zoom: 1
    })
});

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
    if (geomData.id == currentSelectedGeomId) {
        selectMapGeom(geomData.id);
    };
};

function selectMapGeom(adminId) {
    selectedLayer.getSource().clear();
    fromFeat = disambiguationLayer.getSource().getFeatureById(adminId);
    props = fromFeat.getProperties();
    feat = new ol.Feature(props);
    feat.setGeometry(fromFeat.getGeometry());
    selectedLayer.getSource().addFeature(feat);
    // geom extent
    extent = feat.getGeometry().getExtent();
    // pad around extent
    extentWidth = extent[2] - extent[0];
    pad = extentWidth * 0.1;
    extent = ol.extent.buffer(extent, pad, extent);
    // offset extent to the left so geom shows on the right
    offsetFactor = 1;
    offsetLeft = extentWidth * offsetFactor;
    extent[0] = extent[0] - offsetLeft;
    disambiguationMap.getView().fit(extent);
    //disambiguationMap.getView().setZoom(disambiguationMap.getView().getZoom()-1);
}

