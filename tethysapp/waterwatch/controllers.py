from django.shortcuts import render
from .utilities import initLayers
from .app import Waterwatch as app


def home(request):
    """
    Controller for the app home page.
    """

    ponds = initLayers()
    context = {
        'ponds_mapurl': ponds['tile_fetcher'].url_format,
    }
    return render(request, 'waterwatch/home.html', context)
