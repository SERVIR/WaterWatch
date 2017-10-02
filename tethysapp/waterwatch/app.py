from tethys_sdk.base import TethysAppBase, url_map_maker


class Waterwatch(TethysAppBase):
    """
    Tethys app class for Ferlo Ephemeral Water Body Monitoring Dashboard.
    """

    name = 'Ferlo Ephemeral Water Body Monitoring Dashboard'
    index = 'waterwatch:home'
    icon = 'waterwatch/images/logo.png'
    package = 'waterwatch'
    root_url = 'waterwatch'
    color = '#2c3e50'
    description = 'View Ferlo Ephemeral Water Bodies in Senegal'
    tags = 'Hydrology'
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
                name='timeseries',
                url='waterwatch/timeseries',
                controller='waterwatch.ajax_controllers.timeseries'
            ),
            UrlMap(
                name='mnwdi',
                url='waterwatch/mndwi',
                controller='waterwatch.ajax_controllers.mndwi'
            ),
        )

        return url_maps
