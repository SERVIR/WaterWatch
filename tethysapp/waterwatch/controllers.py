from django.shortcuts import render
from .utilities import initLayers,initMndwi
from .app import Waterwatch as app


def home(request):
    """
    Controller for the app home page.
    """

    ponds = initLayers()
    mndwi=initMndwi()
    context = {
        # 'ponds_mapurl': ponds['tile_fetcher'].url_format,
        'mndwiImg_mapid': mndwi,
    }
    return render(request, 'waterwatch/home.html', context)
