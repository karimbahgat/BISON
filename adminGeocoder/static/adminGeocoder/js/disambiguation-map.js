
/////////////
// main country map

// layer
var disambiguationStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgb(6,75,52)'
    }),
    stroke: new ol.style.Stroke({
        color: 'white',
        width: 0.5,
    }),
});
var disambiguationLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: disambiguationStyle,
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
        disambiguationLayer
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

function addGeomToDisambiguationMap(geomData) {
    props = {'id': geomData.id,
            'displayName': 'test' //getDisplayName(matchData)
            };
    feat = {'type': 'Feature',
            'id': geomData.id,
            'properties': props,
            'geometry': geomData['geom']};
    feat = new ol.format.GeoJSON().readFeature(feat, {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
    disambiguationLayer.getSource().addFeature(feat);
    disambiguationMap.getView().fit(disambiguationLayer.getSource().getExtent());
    disambiguationMap.getView().setZoom(disambiguationMap.getView().getZoom()-1);
};

