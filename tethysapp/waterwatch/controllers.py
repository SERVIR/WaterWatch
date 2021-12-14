from django.shortcuts import render
from .utilities import initLayers, initMndwi
from .app import Waterwatch as app
import ee
from . import config
from ee.ee_exception import EEException


def home(request):
    """
    Controller for the app home page.
    """
    try:
        credentials = ee.ServiceAccountCredentials(config.EE_SERVICE_ACCOUNT,
                                                   config.EE_SECRET_KEY)
        ee.Initialize(credentials)
    except EEException:
        ee.Initialize()

    ponds = initLayers()
    mndwi=initMndwi()
    context = {
        # 'ponds_mapurl': ponds['tile_fetcher'].url_format,
        'mndwiImg_mapid': mndwi,
    }
    return render(request, 'waterwatch/home.html', context)
