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
    var current_layer,
        layers,
        map,
        ponds_mapid,
        ponds_token,
        public_interface,				// Object returned by the module
        $tsplotModal;



    /************************************************************************
     *                    PRIVATE FUNCTION DECLARATIONS
     *************************************************************************/

    var init_all,
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

        layers = [base_map,ponds_layer];
        map = new ol.Map({
            target: 'map',
            layers: layers,
            view: new ol.View({
                center: ol.proj.fromLonLat([-14.45,14.4974]),
                zoom: 7
            })
        });
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

        map.on("singleclick",function(evt){
            var clickCoord = evt.coordinate;
            console.log(ol.proj.transform(clickCoord, 'EPSG:3857','EPSG:4326'));
            var proj_coords = ol.proj.transform(clickCoord, 'EPSG:3857','EPSG:4326');
            var $loading = $('#view-file-loading');
            $loading.removeClass('hidden');
            $("#plotter").addClass('hidden');
            $tsplotModal.modal('show');
            var xhr = ajax_update_database('timeseries',{'lat':proj_coords[1],'lon':proj_coords[0]});
            xhr.done(function(data) {
                if("success" in data) {
                    console.log(data.values);
                    $("#plotter").highcharts({
                        chart: {
                            type:'area',
                            zoomType: 'x'
                        },
                        title: {
                            text:'Percent coverage of water at '+Math.round(proj_coords[1],4)+','+Math.round(proj_coords[0],4)
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
                            }

                        },
                        exporting: {
                            enabled: true
                        },
                        series: [{
                            data:data.values,
                            name: 'Percent coverage of water'
                        }]
                    });
                    $loading.addClass('hidden');
                    $("#plotter").removeClass('hidden');
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