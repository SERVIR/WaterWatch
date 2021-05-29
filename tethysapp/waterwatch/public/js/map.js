/*****************************************************************************
 * FILE:    MAP JS
 * DATE:    29 September 2017
 * AUTHOR: Sarva Pulla
 * COPYRIGHT: (c) SERVIR GLOBAL 2017
 * LICENSE: BSD 2-Clause
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/
var LIBRARY_OBJECT = (function() {
    // Wrap the library in a package function
    "use strict"; // And enable strict mode for this library

    /************************************************************************
     *                      MODULE LEVEL / GLOBAL VARIABLES
     *************************************************************************/
    var base_map2,
        current_layer,
        layers,
        map,
        ponds_mapurl,
        ponds_mapid,
        ponds_token,
        public_interface,				// Object returned by the module
        select_feature_source,
        select_feature_layer,
        $chartModal,
        water_source,
        water_layer,
        true_source,
        true_layer;


    /************************************************************************
     *                    PRIVATE FUNCTION DECLARATIONS
     *************************************************************************/

    var generate_chart,
        generate_forecast,
        generate_details,
        init_all,
        init_events,
        init_vars,
        init_map;

    /************************************************************************
     *                    PRIVATE FUNCTION IMPLEMENTATIONS
     *************************************************************************/

    document.getElementById("myInput").onkeyup = function () {
        var input, filter, ul, li, a, i, txtValue;
        input = document.getElementById("myInput");
        filter = input.value.toUpperCase();
        ul = document.getElementById("myUL");
        li = ul.getElementsByTagName("li");
        for (i = 0; i < li.length; i++) {
            a = li[i].getElementsByTagName("a")[0];
            txtValue = a.innerHTML;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                li[i].style.display = "";
            } else {
                li[i].style.display = "none";
            }
        }

    }
    if (localStorage['ponds_url']) {
        var ponds_url = JSON.parse(localStorage['ponds_url']);
        if (new Date(ponds_url.time_created) < new Date().setDate(new Date().getDate() - 1)) {
            ajax_update_database("get-ponds-url", {}).done(function (data) {
                if ("success" in data) {
                    localStorage.setItem('ponds_url', JSON.stringify({
                        'url': data['url'],
                        'time_created': new Date().toString()
                    }))
                }
            });
        }
    } else {
        ajax_update_database("get-ponds-url", {}).done(function (data) {
            if ("success" in data) {
                localStorage.setItem('ponds_url', JSON.stringify({
                    'url': data['url'],
                    'time_created': new Date().toString()
                }))
            }
        });
    }
    ajax_update_database("get-ponds-list", {}).done(function (data) {
        if ("success" in data) {
            var j;
            var obj = [];
            var centers = data['centers'];
            var names = data['names'];
            // var pondsList = data['ponds'];
            // for (j = 0; j < pondsList.length; j++) {
            //     if (pondsList[j]['geometry']['coordinates']) {
            //         var nn = pondsList[j]['geometry']['coordinates'][0];
            //      //   console.log(nn)
            //
            //         var name = pondsList[j]['properties']['Nom'];
            //
            //         if (name.length < 2) name = 'Unnamed pond';
            //         var k;
            //         var xx = 0, yy = 0;
            //         for (k = 0; k < nn.length; k++) {
            //
            //             xx = xx + nn[k][0];
            //             yy = yy + nn[k][1];
            //
            //         }
            //         var center = [ xx / nn.length,yy / nn.length];
            //
            //
            //
            //         if (center[0] && center[1] && !names.includes(name)) {
            //
            //             centers.push(center);
            //             names.push(name);
            //         }
            //     }
            // }
            var i;
            var myNodelist = document.getElementsByTagName("LI");
            var i;
            for (i = 0; i < names.length; i++) {
                var li = document.createElement("li");
                var a = document.createElement('a');
                a.id = centers[i];
                a.innerHTML = names[i];

                a.onclick = function () {

                    //console.log([parseFloat(this.id.split(',')[0]), parseFloat(this.id.split(',')[1])]);

                    //  map.getView().setCenter(ol.proj.transform([parseFloat(this.id.split(',')[0]), parseFloat(this.id.split(',')[1])], 'EPSG:4326', 'EPSG:3857'));
                    //map.getView().setZoom(16);
                    var view = map.getView();
                    view.animate({
                        center: ol.proj.transform([parseFloat(this.id.split(',')[0]), parseFloat(this.id.split(',')[1])], 'EPSG:4326', 'EPSG:3857'),
                        zoom: 16
                    });
                }
                li.appendChild(a);

                document.getElementById("myUL").appendChild(li);

            }


            /*for(i=0;i<names.length;i++) {
                var newbox = document.createElement('input');
                newbox.type = "radio";
                newbox.name = "radiogroup";
                newbox.value = centers[i];
                newbox.onclick = function () {
                    if (this.checked) {
                        console.log([parseFloat(this.value.split(',')[0]), parseFloat(this.value.split(',')[1])]);

                        map.getView().setCenter(ol.proj.transform([parseFloat(this.value.split(',')[0]), parseFloat(this.value.split(',')[1])], 'EPSG:4326', 'EPSG:3857'));
                        map.getView().setZoom(16);
                    }
                }
                var lbl = document.createElement('label');
                lbl.innerHTML = names[i];
                document.getElementById('cboxes').appendChild(newbox);
                document.getElementById('cboxes').appendChild(lbl);
                document.getElementById('cboxes').appendChild(document.createElement('br'));
            }*/
            // autocomplete(document.getElementById("myInput"), names);
        }
    });

    init_vars = function () {

        var $layers_element = $('#layers');

        //ponds_mapid = $layers_element.attr('data-ponds-mapid');
        //ponds_token = $layers_element.attr('data-ponds-token');
        $chartModal = $("#chart-modal");
    };

    init_map = function () {
        var attribution = new ol.Attribution({
            html: 'Tiles © <a href="https://services.arcgisonline.com/ArcGIS/rest/services/">ArcGIS</a>'
        });

        var base_map = new ol.layer.Tile({
            crossOrigin: 'anonymous',
            source: new ol.source.XYZ({
                attributions: [attribution],
                url: 'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/' +
                    'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
            })
        });

        base_map2 = new ol.layer.Tile({
            source: new ol.source.BingMaps({
                key: '5TC0yID7CYaqv3nVQLKe~xWVt4aXWMJq2Ed72cO4xsA~ApdeyQwHyH_btMjQS1NJ7OHKY8BK-W-EMQMrIavoQUMYXeZIQOUURnKGBOC7UCt4',
                imagerySet: 'AerialWithLabels' // Options 'Aerial', 'AerialWithLabels', 'Road'
            })
        });

        var region_layer = new ol.layer.Tile({
            title: 'Region Senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:region_layer', TILED: true}
            }),
            visible: false,
            name: 'region_Senegal'
        });
        console.log('hei');
        var arrondissement_layer = new ol.layer.Tile({
            title: 'Arrondissement Senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:arrondissement_senegal', TILED: true}
            }),
            visible: false,
            name: 'arrondissement_Senegal'
        });
        var departement_layer = new ol.layer.Tile({
            title: 'layer_departement_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:layer_departement_senegal', TILED: true}
            }),
            visible: false,
            name: 'layer_departement_senegal'
        });
        var commune_layer = new ol.layer.Tile({
            title: 'layer_commune_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:layer_commune_senegal', TILED: true}
            }),
            visible: false,
            name: 'layer_commune_senegal'
        });
        var village_layer = new ol.layer.Tile({
            title: 'Village Wendou',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:Village', TILED: true}
            }),
            zIndex: 900,
            visible: false,
            name: 'Village_Wendou'
        });
        var Axe_de_transhumance = new ol.layer.Tile({
            title: 'Axe_de_transhumance',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:Axe_de_transhumance', TILED: true}
            }),
            zIndex: 900,
            visible: false,
            name: 'Axe_de_transhumance'
        });
        var couloirs_sud = new ol.layer.Tile({
            title: 'couloirs_sud',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:couloirs_sud', TILED: true}
            }),
            zIndex: 900,
            visible: false,
            name: 'couloirs_sud'
        });
        var up_senegal = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wms',
                params: {LAYERS: 'wendou:up_senegal', TILED: true}
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_praps = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_pafae = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_prodam = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_padaer = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_pasa = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_pdesoc = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_avsf = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });
        var up_papel = new ol.layer.Tile({
            title: 'up_senegal',
            source: new ol.source.TileWMS({
                url: 'https://wendou_geoserver.csesn.dev/geoserver/wendou/wms?service=WMS&version=1.1.0&request=GetMap&layers=wendou%3AUnite_pastorale&styles=wendou%3Aup&bbox=405129.61089999974%2C1514073.715412192%2C795299.9430384059%2C1822606.6820437144&width=768&height=607&srs=EPSG%3A32628',
            }),
            zIndex: 910,
            visible: false,
            name: 'up_senegal'
        });


        var namestyle = new ol.style.Style({
            text: new ol.style.Text({
                font: '20px Verdana',
                text: 'TZ',
                fill: new ol.style.Fill({
                    color: [64, 64, 64, 0.75]
                })
            })
        });
        var defaultStyles = [
            new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'white'
                }),
                stroke: new ol.style.Stroke({color: 'black', width: 2})
            })
        ];

        var west_africa = new ol.Feature(new ol.geom.Polygon([[[-2025275.5014440303, 1364859.5770601076], [-1247452.3016140766, 1364859.5770601076], [-1247452.3016140766, 1898084.286377496], [-2025275.5014440303, 1898084.286377496], [-2025275.5014440303, 1364859.5770601076]]]));

        var boundary_layer = new ol.layer.Vector({
            title: 'Boundary Layer',
            source: new ol.source.Vector(),
            style: new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: "red",
                    width: 1
                })
            })
        });
        boundary_layer.getSource().addFeatures([west_africa]);
        // var base_map =  new ol.layer.Tile({
        //     crossOrigin:'anonymous',
        //     source: new ol.source.XYZ({
        //       attributions: [attribution],
        //       url: 'https://server.arcgisonline.com/ArcGIS/rest/services/' +
        //           'World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
        //     })
        //   }); //

        var ponds_layer = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: JSON.parse(localStorage['ponds_url']).url //"https://earthengine.googleapis.com/map/"+ponds_mapid+"/{z}/{x}/{y}?token="+ponds_token
            })
        });

        console.log(ponds_layer.getSource());
        var b = ponds_layer.getSource();
        console.log(b.features);
        select_feature_source = new ol.source.Vector();
        select_feature_layer = new ol.layer.Vector({
            source: select_feature_source,
            style: new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: "black",
                    width: 8
                })
            })
        });

        water_source = new ol.source.XYZ();
        water_layer = new ol.layer.Tile({
            source: water_source
            // url:""
        });

        true_source = new ol.source.XYZ();
        true_layer = new ol.layer.Tile({
            source: true_source
            // url:""
        });
        //  var mndwi_layer = new ol.layer.Tile({
        //     source: new ol.source.XYZ({
        //         url: mndwi_mapid
        //             // "https://earthengine.googleapis.com/map/"+mndwi_mapid+"/{z}/{x}/{y}?token="+mndwi_token
        //     }),
        //     visible: true,
        //     name:'mndwi_layer'
        // });

        //  layers = [base_map,base_map2,ponds_layer,true_layer,water_layer,boundary_layer,select_feature_layer];
        layers = [base_map, base_map2, ponds_layer, true_layer, water_layer, select_feature_layer, region_layer, commune_layer, arrondissement_layer, village_layer, departement_layer, Axe_de_transhumance, couloirs_sud, up_praps, up_pafae, up_prodam, up_padaer, up_pasa, up_pdesoc, up_avsf, up_papel];
        map = new ol.Map({
            target: 'map',
            layers: layers,
            view: new ol.View({
                center: ol.proj.fromLonLat([-14.45, 14.4974]),
                zoom: 10
            })
        });
        var params1 = layers[13].getSource().getParams();
        params1.cql_filter = "Projet = 'PRAPS'";
        layers[13].getSource().updateParams(params1);

        var params2 = layers[13].getSource().getParams();
        params2.cql_filter = "Projet = 'PAFA-E'";
        layers[14].getSource().updateParams(params2);

        var params3 = layers[14].getSource().getParams();
        params3.cql_filter = "Projet = 'PRODAM'";
        layers[15].getSource().updateParams(params3);

        var params4 = layers[15].getSource().getParams();
        params4.cql_filter = "Projet = 'PADAER'";
        layers[16].getSource().updateParams(params4);

        var params5 = layers[16].getSource().getParams();
        params5.cql_filter = "Projet = 'PASA'";
        layers[17].getSource().updateParams(params5);

        var params6 = layers[17].getSource().getParams();
        params6.cql_filter = "Projet = 'PDESOC'";
        layers[18].getSource().updateParams(params6);

        var params7 = layers[18].getSource().getParams();
        params7.cql_filter = "Projet = 'AVSF'";
        layers[19].getSource().updateParams(params7);

        var params8 = layers[19].getSource().getParams();
        params8.cql_filter = "Projet = 'PAPEL'";
        layers[20].getSource().updateParams(params8);

        var mouse_position = new ol.control.MousePosition({
            coordinateFormat: ol.coordinate.createStringXY(4),
            projection: 'EPSG:4326',
            className: 'custom-mouse-position',
            target: 'coordonnees',
            undefinedHTML: '&nbsp;'
        });
        map.addControl(mouse_position);

        map.getLayers().item(1).setVisible(false);

        init_events = function () {
            (function () {
                var target, observer, config;
                // select the target node
                target = $('#app-content-wrapper')[0];

                observer = new MutationObserver(function () {
                    window.setTimeout(function () {
                        map.updateSize();
                    }, 350);
                });
                $(window).on('resize', function () {
                    map.updateSize();
                });

                config = {attributes: true};

                observer.observe(target, config);
            }());
        }

        //Map on zoom function. To keep track of the zoom level. Data can only be viewed can only be added at a certain zoom level.
        map.on("moveend", function () {
            var zoom = map.getView().getZoom();
            var zoomInfo = '<p style="color:white;">Current Zoom level = ' + zoom.toFixed(3) + '.</p>';
            document.getElementById('zoomlevel').innerHTML = zoomInfo;
            if (zoom > 14) {
                base_map2.setVisible(true);
            } else {
                base_map2.setVisible(false);
            }
            // Object.keys(layersDict).forEach(function(key){
            //     var source =  layersDict[key].getSource();
            // });
        });


        map.on("singleclick", function (evt) {

            var zoom = map.getView().getZoom();
            $chartModal.modal('show');
            if (zoom < 14) {

                $('.info').html('<b>The zoom level has to be 14 or greater. Please check and try again.</b>');
                $('#info').removeClass('hidden');
                return false;
            } else {
                $('.info').html('');
                $('#info').addClass('hidden');
            }

            var clickCoord = evt.coordinate;
            var proj_coords = ol.proj.transform(clickCoord, 'EPSG:3857', 'EPSG:4326');
            $("#current-lat").val(proj_coords[1]);
            $("#current-lon").val(proj_coords[0]);
            var $loading = $('#view-file-loading');
            var $loadingF = $('#f-view-file-loading');
            $loading.removeClass('hidden');
            $loadingF.removeClass('hidden');
            $("#plotter").addClass('hidden');
            $("#forecast-plotter").addClass('hidden');
            //$tsplotModal.modal('show');

            var myGeoJSON1 = [];
            var myGeoJSON2 = [];
            var mareSelect, buffered;
            var $elements;
            var xhr = ajax_update_database('timeseries', {'lat': proj_coords[1], 'lon': proj_coords[0]}, 'name');
            xhr.done(function (data) {
                if ("success" in data) {
                    $('.info').html('');
                    map.getLayers().item(3).getSource().setUrl("");
                    map.getLayers().item(4).getSource().setUrl("");
                    var polygon = new ol.geom.Polygon(data.coordinates);
                    polygon.applyTransform(ol.proj.getTransform('EPSG:4326', 'EPSG:3857'));
                    var feature = new ol.Feature(polygon);

                    mareSelect = turf.polygon(data.coordinates);

                    buffered = turf.buffer(mareSelect, 10, {units: 'kilometers'});
                    var villagehr = ajax_update_database('coucheVillages');
                    villagehr.done(function (data2) {
                        for (var iter = 0; iter < data2.village.length; iter++) {
                            var buff1 = turf.feature(data2.village[iter].geometry, data2.village[iter].properties);
                            if (turf.booleanWithin(buff1, buffered)) {
                                var ptsWithin = 'Village :' + data2.village[iter].properties['Toponymie'] + '// Population ' + data2.village[iter].properties['EffectifPo'];
                                myGeoJSON1.push(buff1);
                                myGeoJSON2.push(ptsWithin);
                                var x = document.createElement("p");
                                var x1 = document.createElement("b");
                                var t = document.createTextNode(data2.village[iter].properties['Toponymie']);
                                var t1 = document.createTextNode(" avec  " + data2.village[iter].properties['EffectifPo'] + " habitants");
                                x1.appendChild(t);
                                x.appendChild(x1);
                                x.appendChild(t1);
                                var newElement = $('<div>', {text: data2.village[iter].properties['Toponymie'] + '  avec  ' + data2.village[iter].properties['EffectifPo'] + ' habitants'});
                                if ($elements) {
                                    $elements = $($elements).add(x);
                                } else {
                                    $elements = $().add(x);
                                }
                            }
                        }
                        $("#meta-table-village").html('');
                        var h = document.createElement("h2");
                        var titre = document.createTextNode("Villages à 10 km de la mare de " + data.name);
                        h.appendChild(titre);
                        $("#meta-table-village").append(h);
                        $("#meta-table-village").append($elements);
                        $("#reset").removeClass('hidden');

                    });
                    var buffOut1 = turf.featureCollection(myGeoJSON1);

                    map.getLayers().item(5).getSource().clear();
                    select_feature_source.addFeature(feature);

                    generate_chart(data.values, proj_coords[1], proj_coords[0], data.name);

                    $loading.addClass('hidden');
                    $("#plotter").removeClass('hidden');

                } else {
                    $('.info').html('<b>Error processing the request. Please be sure to click on a feature.' + data.error + '</b>');
                    $('#info').removeClass('hidden');
                    $loading.addClass('hidden');

                }
            });


            var yhr = ajax_update_database('forecast', {'lat': proj_coords[1], 'lon': proj_coords[0]}, 'name');
            yhr.done(function (data) {
                if ("success" in data) {
                    $('.info').html('');
                    map.getLayers().item(3).getSource().setUrl("");
                    var polygon = new ol.geom.Polygon(data.coordinates);
                    polygon.applyTransform(ol.proj.getTransform('EPSG:4326', 'EPSG:3857'));
                    var feature = new ol.Feature(polygon);

                    map.getLayers().item(5).getSource().clear();
                    select_feature_source.addFeature(feature);

                    generate_forecast(data.values, proj_coords[1], proj_coords[0], data.name);

                    $loadingF.addClass('hidden');
                    $("#forecast-plotter").removeClass('hidden');

                } else {
                    $('.info').html('<b>Error processing the request. Please be sure to click on a feature.' + data.error + '</b>');
                    $('#info').removeClass('hidden');
                    $loadingF.addClass('hidden');

                }
            });
            var zhr = ajax_update_database('details', {'lat': proj_coords[1], 'lon': proj_coords[0]}, 'name');
            zhr.done(function (data) {
                if ("success" in data) {
                    $('.info').html('');
                    map.getLayers().item(3).getSource().setUrl("");
                    var polygon = new ol.geom.Polygon(data.coordinates);
                    polygon.applyTransform(ol.proj.getTransform('EPSG:4326', 'EPSG:3857'));
                    var feature = new ol.Feature(polygon);

                    map.getLayers().item(5).getSource().clear();
                    select_feature_source.addFeature(feature);
                    generate_details(proj_coords[1], proj_coords[0], data.namePond, data.sup_Pond, data.coordinates, data.nameRegion, data.nameCommune, data.nameArrondissement);

                    $loadingF.addClass('hidden');
                    //                  $("#details-plotter").removeClass('hidden');

                } else {
                    $('.info').html('<b>Erreur lors du traitement de la demande. Assurez-vous de cliquer sur une fonctionnalité.' + data.error + '</b>');
                    $('#info').removeClass('hidden');
                    $loadingF.addClass('hidden');
                }
            });
        });
        //       map.on('pointermove', function(evt) {
        //           if (evt.dragging) {
        //               return;
        //           }
        //           var pixel = map.getEventPixel(evt.originalEvent);
        //           var hit = map.forEachLayerAtPixel(pixel, function(layer) {
        //               if (layer == layers[2]){
        //                   current_layer = layer;
        //                   return true;}
        //           });
        //           map.getTargetElement().style.cursor = hit ? 'pointer' : '';
        // });
    };

    generate_chart = function (data, lat, lon, name) {
        var timeArr = []
        var waterArr = []
        var errArr = []
        var timestamp, water, stddev, minerr, maxerr;
        for (var i = 0; i < data.length; i++) {
            if (data[i][1].water != null) {
                timestamp = data[i][0]
                water = data[i][1].water
                stddev = data[i][1].stddev
                minerr = water - stddev
                maxerr = water + stddev
                if (minerr < 0) {
                    minerr = 0
                }
                if (maxerr > 1) {
                    maxerr = 1
                }
                timeArr.push(timestamp)
                waterArr.push([timestamp, water])
                errArr.push([timestamp, minerr, maxerr])
            }
        }
        Highcharts.stockChart('plotter', {
            chart: {
                type: 'line',
                zoomType: 'x'
            },
            plotOptions: {
                series: {
                    marker: {
                        enabled: true
                    },
                    allowPointSelect: true,
                    cursor: 'pointer',
                    point: {
                        events: {
                            click: function () {
                                $('.info').html('');
                                $("#meta-table").html('');
                                $("#reset").addClass('hidden');
                                $("#layers_checkbox").addClass('hidden');
                                var lat = $("#current-lat").val();
                                var lon = $("#current-lon").val();
                                var xhr = ajax_update_database('mndwi', {
                                    'xValue': this.x,
                                    'yValue': this.y,
                                    'lat': lat,
                                    'lon': lon
                                });
                                xhr.done(function (data) {
                                    if ("success" in data) {
                                        map.getLayers().item(3).getSource().setUrl(data.true_mapurl);
                                        map.getLayers().item(4).getSource().setUrl(data.water_mapurl);
                                        $("#meta-table").append('<tbody><tr><th>Latitude</th><td>' + (parseFloat(lat).toFixed(6)) + '</td></tr><tr><th>Longitude</th><td>' + (parseFloat(lon).toFixed(6)) + '</td></tr><tr><th>Current Date</th><td>' + data.date + '</td></tr><tr><th>Scene Cloud Cover</th><td>' + data.cloud_cover + '</td></tr></tbody>');
                                        $("#reset").removeClass('hidden');
                                        $("#layers_checkbox").removeClass('hidden');
                                    } else {
                                        $('.info').html('<b>Error processing the request. Please be sure to click on a feature.' + data.error + '</b>');
                                        $('#info').removeClass('hidden');
                                        $("#layers_checkbox").addClass('hidden');
                                    }
                                });

                            }
                        }
                    }
                }
            },
            title: {
                text: 'Percent coverage of water at ' + (name) + ' (' + (lon.toFixed(3)) + ',' + (lat.toFixed(3)) + ')'
                // style: {
                //     fontSize: '13px',
                //     fontWeight: 'bold'
                // }
            },
            xAxis: {
                type: 'datetime',
                labels: {
                    format: '{value:%d %b %Y}'
                    // rotation: 90,
                    // align: 'left'
                },
                title: {
                    text: 'Date'
                },
            },
            yAxis: {
                title: {
                    text: '%'
                },
                max: 1,
                min: 0,
            },
            exporting: {
                enabled: true
            },
            series: [{
                data: waterArr,
                name: 'Water coverage',
                tooltip: {
                    pointFormat: '<span style="font-weight: bold;">{series.name}</span>: <b>{point.y:.4f} %</b> '
                }
            },
                {
                    name: 'Water error',
                    type: 'errorbar',
                    data: errArr,
                    tooltip: {
                        pointFormat: '(Coverage range: {point.low:.4f}-{point.high:.4f} %)<br/>'
                    },
                }],
            tooltip: {
                shared: true,
            }
        });
    };
    generate_forecast = function (data, lat, lon, name) {

        var data1 = []
        for (var i = 0; i < data.length; i++) {
            if (data[i][1].water != null) {
                //   data[i][1] = data[i][1].water;
                data1.push([data[i][0], data[i][1].water]);
            }
        }
        Highcharts.stockChart('forecast-plotter', {
            chart: {
                type: 'line',
                zoomType: 'x'
            },
            plotOptions: {
                series: {
                    marker: {
                        enabled: true
                    },
                    allowPointSelect: true,
                    cursor: 'pointer',
                    point: {
                        events: {
                            click: function () {
                                $('.info').html('');
                                $("#meta-table").html('');
                                $("#reset").addClass('hidden');
                                $("#layers_checkbox").addClass('hidden');
                                var lat = $("#current-lat").val();
                                var lon = $("#current-lon").val();
                                var xhr = ajax_update_database('mndwi', {
                                    'xValue': this.x,
                                    'yValue': this.y,
                                    'lat': lat,
                                    'lon': lon
                                });

                                xhr.done(function (data) {
                                    if ("success" in data) {
                                        map.getLayers().item(3).getSource().setUrl(data.true_mapurl);
                                        map.getLayers().item(4).getSource().setUrl(data.water_mapurl);
                                        $("#meta-table").append('<tbody><tr><th>Latitude</th><td>' + (parseFloat(lat).toFixed(6)) + '</td></tr><tr><th>Longitude</th><td>' + (parseFloat(lon).toFixed(6)) + '</td></tr><tr><th>Current Date</th><td>' + data.date + '</td></tr><tr><th>Scene Cloud Cover</th><td>' + data.cloud_cover + '</td></tr></tbody>');
                                        $("#reset").removeClass('hidden');
                                        $("#layers_checkbox").removeClass('hidden');
                                    } else {
                                        $('.info').html('<b>Error processing the request. Please be sure to click on a feature.' + data.error + '</b>');
                                        $('#info').removeClass('hidden');
                                        $("#layers_checkbox").addClass('hidden');
                                    }
                                });

                            }
                        }
                    }
                }
            },
            title: {
                text: 'Percent coverage of water at ' + (name) + ' (' + (lon.toFixed(3)) + ',' + (lat.toFixed(3)) + ')'
                // style: {
                //     fontSize: '13px',
                //     fontWeight: 'bold'
                // }
            },
            xAxis: {
                type: 'datetime',
                labels: {
                    format: '{value:%d %b %Y}'
                    // rotation: 90,
                    // align: 'left'
                },
                title: {
                    text: 'Date'
                }
            },
            yAxis: {
                title: {
                    text: '%'
                },
                max: 1,
                min: 0
            },
            exporting: {
                enabled: true
            },
            series: [{

                data: data1,
                name: 'Forecast percent coverage of water',
                tooltip: {
                    pointFormat: '<span style="font-weight: bold;">{series.name}</span>: <b>{point.y:.4f} %</b> '
                }

            }]
        });
    };

    generate_details = function (lat, lon, namePond, sup_Pond, coordinates, nameRegion, nameCommune, nameArrondissement) {
        $("#meta-table-details").html('');
        $("#meta-table-details").append('<tbody><tr><th>Latitude</th><td>' + (lat.toFixed(6)) + '</td></tr><tr><th>Longitude</th><td>' + (lon.toFixed(6)) + '</td></tr><tr><th>Nom Mare</th><td>' + namePond + '</td></tr><tr><th>Superficie</th><td>' + sup_Pond + '</td></tr><tr><th>Nom région</th><td>' + nameRegion + '</td></tr><tr><th>Nom arrondissement</th><td>' + nameArrondissement + '</td></tr><tr><th>Nom commune</th><td>' + nameCommune + '</td></tr></tbody>');
        $("#reset").removeClass('hidden');

    };
    //onClick="vector_summer.setVisible(!vector_summer.getVisible());"

    init_all = function () {
        init_vars();
        init_map();
        init_events();
    };


    /************************************************************************
     *                        DEFINE PUBLIC INTERFACE
     *************************************************************************/
    /*
     * Library object that contains public facing functions of the package.
     * This is the object that is returned by the library wrapper function.
     * See below.
     * NOTE: The functions in the public interface have access to the private
     * functions of the library because of JavaScript function scope.
     */
    public_interface = {};

    /************************************************************************
     *                  INITIALIZATION / CONSTRUCTOR
     *************************************************************************/

    // Initialization: jQuery function that gets called when
    // the DOM tree finishes loading

    $(function () {
        init_all();
        $(".alert").click(function () {
            $(".alert").alert("close");
        });

        $('#true_toggle').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {

                map.getLayers().item(3).setVisible(true);
            } else {
                map.getLayers().item(3).setVisible(false);
            }
        });

        $('#mndwi_toggle').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {

                map.getLayers().item(4).setVisible(true);
            } else {
                map.getLayers().item(4).setVisible(false);
            }
        });

        $('#ponds_toggle').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {

                map.getLayers().item(2).setVisible(true);
            } else {

                map.getLayers().item(2).setVisible(false);
            }
        });

        $('#select_region_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(6).setVisible(true);
            } else {
                map.getLayers().item(6).setVisible(false);
            }
        });
        $('#select_commune_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(7).setVisible(true);
            } else {
                map.getLayers().item(7).setVisible(false);
            }
        });
        $('#select_arrondissement_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(8).setVisible(true);
            } else {
                map.getLayers().item(8).setVisible(false);
            }
        });
        $('#select_village_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(9).setVisible(true);
            } else {
                map.getLayers().item(9).setVisible(false);
            }
        });
        $('#select_departement_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(10).setVisible(true);
            } else {
                map.getLayers().item(10).setVisible(false);
            }
        });
        $('#select_Axe_de_transhumance_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(11).setVisible(true);
            } else {
                map.getLayers().item(11).setVisible(false);
            }
        });
        $('#select_couloir_de_transhumance_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(12).setVisible(true);
            } else {
                map.getLayers().item(12).setVisible(false);
            }
        });
        $('#praps_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(13).setVisible(true);
            } else {
                map.getLayers().item(13).setVisible(false);
            }
        });
        $('#pafae_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(14).setVisible(true);
            } else {
                map.getLayers().item(14).setVisible(false);
            }
        });
        $('#prodam_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(15).setVisible(true);
            } else {
                map.getLayers().item(15).setVisible(false);
            }
        });
        $('#padaer_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(16).setVisible(true);
            } else {
                map.getLayers().item(16).setVisible(false);
            }
        });
        $('#pasa_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(17).setVisible(true);
            } else {
                map.getLayers().item(17).setVisible(false);
            }
        });
        $('#pdesoc_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(18).setVisible(true);
            } else {
                map.getLayers().item(18).setVisible(false);
            }
        });
        $('#avsf_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(19).setVisible(true);
            } else {
                map.getLayers().item(19).setVisible(false);
            }
        });
        $('#papel_layer').change(function () {
            // this will contain a reference to the checkbox
            if (this.checked) {
                map.getLayers().item(20).setVisible(true);
            } else {
                map.getLayers().item(20).setVisible(false);
            }
        });
    });

    return public_interface;

}()); // End of package wrapper
// NOTE: that the call operator (open-closed parenthesis) is used to invoke the library wrapper
// function immediately after being parsed.
