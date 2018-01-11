import ee
from ee.ee_exception import EEException
import requests
import json
import math
import numpy as np
import datetime,time

try:
    ee.Initialize()
except EEException as e:
    from oauth2client.service_account import ServiceAccountCredentials
    credentials = ServiceAccountCredentials.from_p12_keyfile(
    service_account_email='',
    filename='',
    private_key_password='notasecret',
    scopes=ee.oauth.SCOPE + ' https://www.googleapis.com/auth/drive ')
    ee.Initialize(credentials)

def s2CloudMask(img):
    qa = img.select('QA60');

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloudBitMask = int(math.pow(2, 10));
    cirrusBitMask = int(math.pow(2, 11));

    # clear if both flags set to zero.
    clear = qa.bitwiseAnd(cloudBitMask).eq(0).And(
             qa.bitwiseAnd(cirrusBitMask).eq(0));

    return img.divide(10000).updateMask(clear).set('system:time_start',img.get('system:time_start'))


def lsCloudMask(img):
    blank = ee.Image(0)
    scored = ee.Algorithms.Landsat.simpleCloudScore(img)
    clouds = blank.where(scored.select(['cloud']).lte(cloudThresh), 1)
    return img.updateMask(clouds).set("system:time_start", img.get("system:time_start"))


def lsTOA(img):
    return ee.Algorithms.Landsat.TOA(img)


def mergeCollections(l8, s2, studyArea, t1, t2):
    lc8rename = l8.filterBounds(studyArea).filterDate(t1, t2).map(lsTOA).filter(
        ee.Filter.lt('CLOUD_COVER', 75)).map(lsCloudMask).select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
                                                                 ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])

    st2rename = s2.filterBounds(studyArea).filterDate(t1, t2).filter(
        ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', 75)).map(s2CloudMask).select(
        ['B2', 'B3', 'B4', 'B8', 'B11', 'B12'],
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']).map(bandPassAdjustment)

    return lc8rename


def bandPassAdjustment(img):
    bands = ['blue','green','red','nir','swir1','swir2'];
    # linear regression coefficients for adjustment
    gain = ee.Array([[0.977], [1.005], [0.982], [1.001], [1.001], [0.996]]);
    bias = ee.Array([[-0.00411],[-0.00093],[0.00094],[-0.00029],[-0.00015],[-0.00097]]);
    # Make an Array Image, with a 1-D Array per pixel.
    arrayImage1D = img.select(bands).toArray();

    # Make an Array Image with a 2-D Array per pixel, 6x1.
    arrayImage2D = arrayImage1D.toArray(1);

    componentsImage = ee.Image(gain).multiply(arrayImage2D).add(ee.Image(bias))\
    .arrayProject([0])\
    .arrayFlatten([bands]).float();

    return componentsImage.set('system:time_start',img.get('system:time_start'));


def simpleTDOM2(collection, zScoreThresh, shadowSumThresh, dilatePixels):
    def darkMask(img):
        zScore = img.select(shadowSumBands).subtract(irMean).divide(irStdDev)
        irSum = img.select(shadowSumBands).reduce(ee.Reducer.sum())
        TDOMMask = zScore.lt(zScoreThresh).reduce(ee.Reducer.sum()).eq(2).And(irSum.lt(shadowSumThresh)).Not()
        TDOMMask = TDOMMask.focal_min(dilatePixels)
        return img.addBands(TDOMMask.rename(['TDOMMask']))

    shadowSumBands = ['nir', 'swir1']
    irStdDev = collection.select(shadowSumBands).reduce(ee.Reducer.stdDev())
    irMean = collection.select(shadowSumBands).mean()
    collection.select(shadowSumBands).mean()

    collection = collection.map(darkMask)

    return collection


def calcWaterIndex(img):
    mndwi = img.normalizedDifference(['green', 'swir1']).rename(['mndwi'])

    return mndwi.copyProperties(img, ["system:time_start","CLOUD_COVER"])


def waterClassifier(img):
    THRESHOLD = ee.Number(-0.2)

    mask = img.mask()

    water = ee.Image(0).where(mask, img.select('mndwi').gt(THRESHOLD))

    result = img.addBands(water.rename(['water']))
    return result.copyProperties(img, ["system:time_start","CLOUD_COVER"])


def pondClassifier(shape):
    latest = ee.Image(waterCollection.select('water').filterBounds(shape.geometry()).first())

    avg = latest.reduceRegion(
        reducer=ee.Reducer.mean(),
        scale=30,
        geometry=shape.geometry(),
        bestEffort=True
    )

    try:
        val = ee.Number(avg.get('water'))

        cls = val.gt(0.25)

        cls = cls.add(val.gt(0.75))
    except:
        val = np.random.choice(2, 1)
        cls = ee.Number(val[0])

    return ee.Feature(shape).set({'pondCls': cls.int8()})

def makeTimeSeries(feature):

    def reducerMapping(img):
        reduction = img.reduceRegion(
            ee.Reducer.mean(), feature.geometry(), 30)

        time = img.get('system:time_start')

        return img.set('indexVal',[ee.Number(time),reduction.get('water')])

    collection = waterCollection.select('water').filterBounds(feature.geometry()) #.getInfo()

    indexCollection = collection.map(reducerMapping)

    indexSeries = indexCollection.aggregate_array('indexVal').getInfo()

    formattedSeries = [[x[0],round(float(x[1]),3)] for x in indexSeries]

    days_with_data = [[datetime.datetime.fromtimestamp((int(x[0]) / 1000)).strftime('%Y %B %d'),round(float(x[1]),3)] for x in indexSeries if x[1] > 0 ]

    return sorted(formattedSeries)

def getClickedImage(xValue,yValue,feature):

    equalDate = ee.Date(int(xValue))

    water_image = ee.Image(waterCollection.select('mndwi').filterBounds(feature.geometry()).filterDate(equalDate,equalDate.advance(1,'day')).first())

    water_imageid = water_image.getMapId({'min':-0.3,'max':0.3,'palette':'d3d3d3,84adff,9698d1,0000cc'})

    properties =  water_image.getInfo()['properties']

    return water_imageid,properties

studyArea = ee.Geometry.Rectangle([-15.866, 14.193, -12.990, 16.490])
lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT')
st2 = ee.ImageCollection('COPERNICUS/S2')
ponds = ee.FeatureCollection('users/kelmarkert/public/ferloPonds')
today = time.strftime("%Y-%m-%d")

iniTime = ee.Date('2015-01-01')
endTime = ee.Date(today)

dilatePixels = 2
zScoreThresh = -0.75
shadowSumThresh = 0.35
cloudThresh = 5

mergedCollection = mergeCollections(lc8, st2, studyArea, iniTime, endTime).sort('system:time_start', False)

mergedCollection = simpleTDOM2(mergedCollection, zScoreThresh, shadowSumThresh, dilatePixels)

mndwiCollection = mergedCollection.map(calcWaterIndex)

waterCollection = mndwiCollection.map(waterClassifier)

ponds_cls = ponds.map(pondClassifier)

visParams = {'min': 0, 'max': 2, 'palette': 'red,yellow,green'}

pondsImg = ponds_cls.reduceToImage(properties=['pondCls'],
                                   reducer=ee.Reducer.first())

pondsImgID = pondsImg.getMapId(visParams)

img = mergedCollection.median().clip(studyArea)

mndwiImg = mndwiCollection.median().clip(studyArea)

def initLayers():
    return pondsImgID


def filterPond(lon, lat):
    point = ee.Geometry.Point(float(lon), float(lat))
    sampledPoint = ee.Feature(ponds.filterBounds(point).first())

    computedValue = sampledPoint.getInfo()['properties']['uniqID']

    selPond = ponds.filter(ee.Filter.eq('uniqID', computedValue))

    return selPond

def checkFeature(lon,lat):

    selPond = filterPond(lon,lat)

    ts_values = makeTimeSeries(selPond)
    coordinates = selPond.getInfo()['features'][0]['geometry']['coordinates']
    return ts_values,coordinates

def getMNDWI(lon,lat,xValue,yValue):

    selPond = filterPond(lon, lat)

    mndwi_img = getClickedImage(xValue,yValue,selPond)

    return mndwi_img
