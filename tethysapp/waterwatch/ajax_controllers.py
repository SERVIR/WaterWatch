from .utilities import *
import json
from django.http import JsonResponse
import datetime
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def getPondsUrl(request):

    return_obj = {}


    if request.is_ajax() and request.method == 'POST':

        try:
            return_obj["url"] = initLayers()
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)
    return JsonResponse(return_obj)

@csrf_exempt
def getPondsList(request):

    return_obj = {}


    if request.is_ajax() and request.method == 'POST':

        try:
            x= pondsList()
            return_obj["ponds"]=x
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)
    return JsonResponse(return_obj)

def timeseries(request):

    return_obj = {}


    if request.is_ajax() and request.method == 'POST':

        info = request.POST
        lat = info.get('lat')
        lon = info.get('lon')

        try:
            ts_vals,coordinates,name = checkFeature(lon,lat)
            return_obj["values"] = ts_vals
            return_obj["coordinates"] = coordinates
            return_obj["name"] = name
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
        ts_vals,coordinates,name = forecastFeature(lon,lat)
        return_obj["values"] = ts_vals
        return_obj["coordinates"] = coordinates
        return_obj["name"] = name
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
        clicked_date = datetime.datetime.fromtimestamp((int(x_val) / 1000)).strftime('%Y %B %d')
        lat = info.get('lat')
        lon = info.get('lon')

        try:
            true_img,mndwi_img,properties = getMNDWI(lon,lat,x_val,y_val)
            return_obj['water_mapurl'] = mndwi_img['tile_fetcher'].url_format
            return_obj['true_mapurl'] = true_img['tile_fetcher'].url_format
            return_obj["date"] = clicked_date
            return_obj["cloud_cover"] = properties["CLOUD_COVER"]
            return_obj["success"] = "success"

        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)

    return JsonResponse(return_obj)
def details(request):

    return_obj = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST
        lat = info.get('lat')
        lon = info.get('lon')

        try:
            ponds = filterPond(lon,lat)
            region = filterRegion(lon,lat)
            commune = filterCommune(lon,lat)
            arrondissement = filterArrondissement(lon,lat)
            namePond = ponds.getInfo()['features'][0]['properties']['Nom']
            if len(namePond) < 2:
                namePond = 'Unnamed Pond'

            coordinates = ponds.getInfo()['features'][0]['geometry']['coordinates']

            sup_Pond = ponds.getInfo()['features'][0]['properties']['Sup']
            nameRegion = region.getInfo()['features'][0]['properties']['nom']
            nameCommune = commune.getInfo()['features'][0]['properties']['nom']
            nameArrondissement = arrondissement.getInfo()['features'][0]['properties']['nom']

            return_obj["namePond"] = namePond
            return_obj["sup_Pond"] = sup_Pond
            return_obj["coordinates"] = coordinates
            return_obj["nameRegion"] = nameRegion
            return_obj["nameCommune"] = nameCommune
            return_obj["nameArrondissement"] = nameArrondissement
            return_obj["success"] = "success"
        except Exception as e:
            return_obj["error"] = "Error Processing Request. Error: "+ str(e)
        print("processing complete...")

    return JsonResponse(return_obj)

def coucheVillages(request):
    return_obj = {}
    if request.is_ajax() and request.method == 'POST':
        try:
            village = checkVillage()
            return_obj["village"] = village
            return_obj["success"] = "success"
        except Exception as e:
            return_obj["error"] = _("Error Processing Request. Error: ")+ str(e)
    return JsonResponse(return_obj)