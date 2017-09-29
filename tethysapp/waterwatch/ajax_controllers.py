from utilities import *
import json
from django.http import JsonResponse

def timeseries(request):

    return_obj = {}


    if request.is_ajax() and request.method == 'POST':

        info = request.POST
        lat = info.get('lat')
        lon = info.get('lon')
        try:
            ts_vals = checkFeature(lon,lat)
            return_obj["values"] = ts_vals
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)
    return JsonResponse(return_obj)