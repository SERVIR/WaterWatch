from django.http import JsonResponse
import json
from .utilities import *

def api_get_ponds(request):

    json_obj = {}
    if request.method == 'GET':

        try:
            ponds = initLayers()
            json_obj = {
                'ponds_mapid': ponds['mapid'],
                'ponds_token': ponds['token'],
                'success':'success'
            }
        except:
            json_obj = {"Error": "Error Processing Request"}

    return  JsonResponse(json_obj)


def api_get_timeseries(request):
    json_obj = {}

    if request.method == 'GET':

        info = request.GET
        lat = info.get('latitude')
        lon = info.get('longitude')

        try:
            ts_vals,coordinates,name = checkFeature(lon,lat)
            json_obj["values"] = ts_vals
            json_obj["coordinates"] = coordinates
            json_obj["name"] = name
            json_obj["success"] = "success"

        except Exception as e:
            json_obj["error"] = "Error Processing Request. Error: "+ str(e)
    return JsonResponse(json_obj)
