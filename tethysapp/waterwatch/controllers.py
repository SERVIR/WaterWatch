from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tethys_sdk.gizmos import *
from utilities import *

def home(request):
    """
    Controller for the app home page.
    """
    ponds = initLayers()

    context = {
        'ponds_mapid':ponds['mapid'],
        'ponds_token':ponds['token']
    }

    return render(request, 'waterwatch/home.html', context)