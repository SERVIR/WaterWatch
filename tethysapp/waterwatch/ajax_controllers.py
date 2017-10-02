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
            ts_vals,coordinates = checkFeature(lon,lat)
            return_obj["values"] = ts_vals
            return_obj["coordinates"] = coordinates
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)
    return JsonResponse(return_obj)

def mndwi(request):

    return_obj = {}

    if request.is_ajax() and request.method == 'POST':

        info = request.POST
        x_val = info.get('xValue')
        y_val = info.get('yValue')
        lat = info.get('lat')
        lon = info.get('lon')

        print x_val,y_val,lon,lat

        try:
            mndwi_img = getMNDWI(lon,lat,x_val,y_val)
            print mndwi_img["mapid"],mndwi_img["token"]
            return_obj["water_mapid"] = mndwi_img["mapid"]
            return_obj["water_token"] = mndwi_img["token"]
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)

    return JsonResponse(return_obj)