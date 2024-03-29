from tethys_sdk.base import TethysAppBase, url_map_maker

class Waterwatch(TethysAppBase):
    """
    Tethys app class for Ferlo Ephemeral Water Body Monitoring Dashboard.
    """

    name = 'Ferlo Ephemeral Water Body Monitoring Dashboard'
    index = 'waterwatch:home'
    icon = 'waterwatch/images/logo_2.png'
    package = 'waterwatch'
    root_url = 'waterwatch'
    color = '#2c3e50'
    description = 'View Ferlo Ephemeral Water Bodies in Senegal'
    tags = 'Hydrology', 'Remote-Sensing'
    enable_feedback = False
    feedback_emails = []
    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (
            UrlMap(
                name='home',
                url='waterwatch',
                controller='waterwatch.controllers.home'
            ),
            UrlMap(
                name='get-ponds-url',
                url='waterwatch/get-ponds-url',
                controller='waterwatch.ajax_controllers.getPondsUrl'
            ),
            UrlMap(
                name='get-ponds-list',
                url='waterwatch/get-ponds-list',
                controller='waterwatch.ajax_controllers.getPondsList'
            ),
            UrlMap(
                name='timeseries',
                url='waterwatch/timeseries',
                controller='waterwatch.ajax_controllers.timeseries'
            ),
            UrlMap(
                name='forecast',
                url='waterwatch/forecast',
                controller='waterwatch.ajax_controllers.forecast'
            ),
            UrlMap(
                name='mndwi',
                url='waterwatch/mndwi',
                controller='waterwatch.ajax_controllers.mndwi'
            ),
            UrlMap(
                name='getPonds',
                url='waterwatch/api/getPonds',
                controller='waterwatch.api.api_get_ponds'
            ),
            UrlMap(
                name='getTimeseries',
                url='waterwatch/api/getTimeseries',
                controller='waterwatch.api.api_get_timeseries'
            ),
            UrlMap(
                name='details',
                url='waterwatch/details',
                controller='waterwatch.ajax_controllers.details'
            ),
            UrlMap(
                name='coucheVillages',
                url='waterwatch/coucheVillages',
                controller='waterwatch.ajax_controllers.coucheVillages'
            ),
        )

        return url_maps

