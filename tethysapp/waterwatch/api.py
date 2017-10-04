from django.http import JsonResponse
import json
from utilities import *

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

        latitude = None
        longitude = None

        if request.GET.get('latitude'):
            latitude = request.GET['latitude']
        if request.GET.get('longitude'):
            longitude = request.GET['longitude']

        try:
            ts_vals,coordinates = checkFeature(longitude,latitude)
            json_obj["values"] = ts_vals
            json_obj["coordinates"] = coordinates
            json_obj["success"] = "success"

        except Exception as e:
            json_obj["error"] = "Error Processing Request. Error: "+ str(e)

    return JsonResponse(json_obj)