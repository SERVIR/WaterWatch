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
        ponds_mapid,
        ponds_token,
        public_interface,				// Object returned by the module
        select_feature_source,
        select_feature_layer,
        $tsplotModal,
        water_source,
        water_layer;



    /************************************************************************
     *                    PRIVATE FUNCTION DECLARATIONS
     *************************************************************************/

    var generate_chart,
        init_all,
        init_events,
        init_vars,
        init_map;

    /************************************************************************
     *                    PRIVATE FUNCTION IMPLEMENTATIONS
     *************************************************************************/

    init_vars = function(){
        var $layers_element = $('#layers');
        ponds_mapid = $layers_element.attr('data-ponds-mapid');
        ponds_token = $layers_element.attr('data-ponds-token');
        $tsplotModal = $("#ts-plot-modal");
    };

    init_map = function(){
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



        var west_africa = new ol.Feature(new ol.geom.Polygon([[[-2025275.5014440303,1364859.5770601076],[-1247452.3016140766,1364859.5770601076],[-1247452.3016140766,1898084.286377496],[-2025275.5014440303,1898084.286377496],[-2025275.5014440303,1364859.5770601076]]]));

        var boundary_layer = new ol.layer.Vector({
            title:'Boundary Layer',
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
        //   });

        var ponds_layer = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: "https://earthengine.googleapis.com/map/"+ponds_mapid+"/{z}/{x}/{y}?token="+ponds_token
            })
        });

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

        layers = [base_map,base_map2,ponds_layer,water_layer,boundary_layer,select_feature_layer];
        map = new ol.Map({
            target: 'map',
            layers: layers,
            view: new ol.View({
                center: ol.proj.fromLonLat([-14.45,14.4974]),
                zoom: 10
            })
        });

        map.getLayers().item(1).setVisible(false);
    };




    init_events = init_events = function() {
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

        //Map on zoom function. To keep track of the zoom level. Data can only be viewed can only be added at a certain zoom level.
        map.on("moveend", function() {
            var zoom = map.getView().getZoom();
            var zoomInfo = '<h6>Current Zoom level = ' + zoom+'</h6>';
            document.getElementById('zoomlevel').innerHTML = zoomInfo;
            if (zoom > 14){
                base_map2.setVisible(true);
            }else{
                base_map2.setVisible(false);
            }
            // Object.keys(layersDict).forEach(function(key){
            //     var source =  layersDict[key].getSource();
            // });
        });


        map.on("singleclick",function(evt){

            var zoom = map.getView().getZoom();
            if (zoom < 16){

                $('.info').html('<b>The zoom level has to be 16 or greater. Please check and try again.</b>');
                $('#info').removeClass('hidden');
                return false;
            }else{
                $('.info').html('');
                $('#info').addClass('hidden');
            }
            var clickCoord = evt.coordinate;
            var proj_coords = ol.proj.transform(clickCoord, 'EPSG:3857','EPSG:4326');
            $("#current-lat").val(proj_coords[1]);
            $("#current-lon").val(proj_coords[0]);
            var $loading = $('#view-file-loading');
            $loading.removeClass('hidden');
            $("#plotter").addClass('hidden');
            //$tsplotModal.modal('show');
            var xhr = ajax_update_database('timeseries',{'lat':proj_coords[1],'lon':proj_coords[0]});
            xhr.done(function(data) {
                if("success" in data) {
                    $('.info').html('');
                    map.getLayers().item(3).getSource().setUrl("");
                    var polygon = new ol.geom.Polygon(data.coordinates);
                    polygon.applyTransform(ol.proj.getTransform('EPSG:4326', 'EPSG:3857'));
                    var feature = new ol.Feature(polygon);

                    map.getLayers().item(5).getSource().clear();
                    select_feature_source.addFeature(feature);

                    generate_chart(data.values,proj_coords[1],proj_coords[0]);
                    $loading.addClass('hidden');
                    $("#plotter").removeClass('hidden');

                }else{
                    $('.info').html('<b>Error processing the request. Please be sure to click on a feature.'+data.error+'</b>');
                    $('#info').removeClass('hidden');
                    $loading.addClass('hidden');

                }
            });
        });
        // map.on('pointermove', function(evt) {
        //     if (evt.dragging) {
        //         return;
        //     }
        //     var pixel = map.getEventPixel(evt.originalEvent);
        //     var hit = map.forEachLayerAtPixel(pixel, function(layer) {
        //         if (layer != layers[0]){
        //             current_layer = layer;
        //             return true;}
        //     });
        //     map.getTargetElement().style.cursor = hit ? 'pointer' : '';
        // });
    };

    generate_chart = function(data,lat,lon){
        Highcharts.stockChart('plotter',{
            chart: {
                type:'line',
                zoomType: 'x'
            },
            plotOptions: {
                series: {
                    marker: {
                        enabled: true
                    },
                    allowPointSelect:true,
                    cursor: 'pointer',
                    point: {
                        events: {
                            click: function () {
                                $('.info').html('');
                                $("#meta-table").html('');
                                $("#reset").addClass('hidden');
                                var lat = $("#current-lat").val();
                                var lon = $("#current-lon").val();
                                var xhr = ajax_update_database('mndwi',{'xValue':this.x,'yValue':this.y,'lat':lat,'lon':lon});
                                xhr.done(function(data) {
                                    if("success" in data) {
                                        map.getLayers().item(3).getSource().setUrl("https://earthengine.googleapis.com/map/"+data.water_mapid+"/{z}/{x}/{y}?token="+data.water_token);
                                        $("#meta-table").append('<tbody><tr><th>Latitude</th><td>'+lat.toFixed(6)+'</td></tr><tr><th>Longitude</th><td>'+lon.toFixed(6)+'</td></tr><tr><th>Current Date</th><td>'+data.date+'</td></tr><tr><th>Scene Cloud Cover</th><td>'+data.cloud_cover+'</td></tr></tbody>');
                                        $("#reset").removeClass('hidden');
                                    }else{
                                        $('.info').html('<b>Error processing the request. Please be sure to click on a feature.'+data.error+'</b>');
                                        $('#info').removeClass('hidden');
                                    }
                                });

                            }
                        }
                    }
                }
            },
            title: {
                text:'Percent coverage of water at '+(lon.toFixed(3))+','+(lat.toFixed(3))
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
                max: 1
            },
            exporting: {
                enabled: true
            },
            series: [{
                data:data,
                name: 'Percent coverage of water'
            }]
        });
    };
    init_all = function(){
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
    public_interface = {

    };

    /************************************************************************
     *                  INITIALIZATION / CONSTRUCTOR
     *************************************************************************/

    // Initialization: jQuery function that gets called when
    // the DOM tree finishes loading

    $(function() {


        init_all();
    });

    return public_interface;

}()); // End of package wrapper
// NOTE: that the call operator (open-closed parenthesis) is used to invoke the library wrapper
// function immediately after being parsed.