import ee
import requests
import json
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

def rescale(img, exp, thresholds):
    return img.expression(exp, {img: img}).subtract(thresholds[0]).divide(thresholds[1] - thresholds[0])


def s2CloudMask(img):
    score = ee.image(1.0)
    score = score.min(rescale(img, 'img.B2', [2000, 3000]))
    score = score.min(rescale(img, 'img.B4 + img.B3 + img.B2', [1900, 8000]))

    score = score.min(
        rescale(img, 'img.B8 + img.B11 + img.B12', [2000, 8000]))

    ndsi = img.normalizedDifference(['B3', 'B11'])
    score = score.min(rescale(ndsi, 'img', [0.8, 0.6]))
    score = score.min(rescale(img, 'img.B10', [10, 100]))
    score = score.multiply(100).byte().lt(15).rename(score, 'cloudMask')
    img = img.updateMask(score)
    return img.divide(10000)


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

    # st2rename = s2.filterBounds(studyArea).filterDate(t1, t2).filter(
    #     ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', 75)).map(s2CloudMask).select(
    #     ['B2', 'B3', 'B4', 'B8', 'B11', 'B12'],
    #     ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])

    return lc8rename


def simpleTDOM2(collection, zScoreThresh, shadowSumThresh, dilatePixels):
    def darkMask(img):
        zScore = img.select(shadowSumBands).subtract(irMean).divide(irStdDev)
        irSum = img.select(shadowSumBands).reduce(ee.Reducer.sum())
        TDOMMask = zScore.lt(zScoreThresh).reduce(ee.Reducer.sum()).eq(2).And(irSum.lt(shadowSumThresh)).Not()
        # not ()
        # zScore.lt(zScoreThresh).reduce(ee.Reducer.sum()).eq(2). and (irSum.lt(shadowSumThresh)).not ()
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

    return mndwi.set("system:time_start", img.get("system:time_start"))


def waterClassifier(img):
    THRESHOLD = ee.Number(-0.2)

    mask = img.mask()

    water = ee.Image(0).where(mask, img.select('mndwi').gt(THRESHOLD))

    result = img.addBands(water.rename(['water']))
    return result.set("system:time_start", img.get("system:time_start"))


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

    return indexSeries

def getClickedImage(xValue,yValue,feature):

    equalDate = ee.Date(int(xValue))

    image = ee.Image(waterCollection.select('mndwi').filterBounds(feature.geometry()).filterDate(equalDate,equalDate.advance(1,'day')).first())

    imageId = image.getMapId({'min':-0.3,'max':0.3,'palette':'d3d3d3,84adff,9698d1,0000cc'})

    return imageId

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

    mndwiImg = getClickedImage(xValue,yValue,selPond)

    return mndwiImg



