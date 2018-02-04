from utilities import *
import json
from django.http import JsonResponse
import datetime

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

def forecast(request):

    return_obj = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST
        lat = info.get('lat')
        lon = info.get('lon')

    try:
        ts_vals,coordinates = forecastFeature(lon,lat)
        return_obj["values"] = ts_vals
        return_obj["coordinates"] = coordinates
        return_obj["success"] = "success"
    except Exception as e:
        return_obj["error"] = "Error Processing Request. Error: "+ str(e)

    print("processing complete...")

    return JsonResponse(return_obj)

def mndwi(request):

    return_obj = {}

    if request.is_ajax() and request.method == 'POST':

        info = request.POST
        x_val = info.get('xValue')
        y_val = info.get('yValue')
        clicked_date = datetime.datetime.fromtimestamp((int(x_val) / 1000)).strftime('%Y %B %d')

        lat = info.get('lat')
        lon = info.get('lon')

        try:
            mndwi_img,properties = getMNDWI(lon,lat,x_val,y_val)
            return_obj["water_mapid"] = mndwi_img["mapid"]
            return_obj["water_token"] = mndwi_img["token"]
            return_obj["date"] = clicked_date
            return_obj["cloud_cover"] = properties["CLOUD_COVER"]
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)

    return JsonResponse(return_obj)
