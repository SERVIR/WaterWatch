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


def rescale(img, thresholds):
    return img.subtract(thresholds[0]).divide(thresholds[1] - thresholds[0])


def s2CloudMask(img):
    score = ee.Image(1.0)
    qa = img.select("QA60").unmask()

    score = score.min(rescale(img.select(['B2']), [0.1, 0.5]))
    score = score.min(rescale(img.select(['B1']), [0.1, 0.3]))
    score = score.min(rescale(img.select(['B1']).add(img.select(['B10'])), [0.15, 0.2]))
    score = score.min(rescale(img.select(['B4']).add(img.select(['B3'])).add(img.select('B2')), [0.2, 0.8]))

    #Clouds are moist
    ndmi = img.normalizedDifference(['B8A','B11'])
    score=score.min(rescale(ndmi, [-0.1, 0.1]))

    # However, clouds are not snow.
    ndsi = img.normalizedDifference(['B3', 'B11'])
    score=score.min(rescale(ndsi, [0.8, 0.6]))
    score = score.multiply(100).byte().lte(10).rename(['cloudMask'])
    img = img.updateMask(score.Or(qa.lt(1024)))
    return img.divide(10000).set("system:time_start", img.get("system:time_start"))


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
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])#.map(bandPassAdjustment)

    return ee.ImageCollection(lc8rename.merge(st2rename))


def bandPassAdjustment(img):
    bands = ['blue','green','red','nir','swir1','swir2']
    # linear regression coefficients for adjustment
    gain = ee.Array([[0.977], [1.005], [0.982], [1.001], [1.001], [0.996]])
    bias = ee.Array([[-0.00411],[-0.00093],[0.00094],[-0.00029],[-0.00015],[-0.00097]])
    # Make an Array Image, with a 1-D Array per pixel.
    arrayImage1D = img.select(bands).toArray()

    # Make an Array Image with a 2-D Array per pixel, 6x1.
    arrayImage2D = arrayImage1D.toArray(1)

    componentsImage = ee.Image(gain).multiply(arrayImage2D).add(ee.Image(bias))\
    .arrayProject([0])\
    .arrayFlatten([bands]).float()

    return componentsImage.set('system:time_start',img.get('system:time_start'))


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

def makeTimeSeries(collection,feature,key=None):

    def reducerMapping(img):
        reduction = img.reduceRegion(
            ee.Reducer.mean(), feature.geometry(), 30)

        time = img.get('system:time_start')

        return img.set('indexVal',[ee.Number(time),reduction.get(key)])

    collection = collection.filterBounds(feature.geometry()) #.getInfo()

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

def accumGFS(collection,startDate,nDays):
  if (nDays>16):
    raise Warning('Max forecast days is 16, only producing forecast for 16 days...')
    nDays = 16

  cnt = 1
  imgList = []
  precipScale = ee.Image(1).divide(ee.Image(1e3))
  for i in range(nDays+1):
    cntMax =(24*(i+1))
    forecastMeta = []
    for j in range(cnt,cntMax+1):
        forecastMeta.append(cnt)
        cnt+=1

    dayPrecip = collection.filter(ee.Filter.inList('forecast_hours', forecastMeta))
    imgList.append(dayPrecip.sum().multiply(precipScale)
      .set('system:time_start',startDate.advance(i,'day')))

  return ee.ImageCollection(imgList)


def accumCFS(collection,startDate,nDays):
    imgList = []
    precipScale = ee.Image(86400).divide(ee.Image(1e3))
    for i in range(nDays):
        newDate = startDate.advance(i,'day')
        dayPrecip = collection.filterDate(newDate,newDate.advance(24,'hour'))
        imgList.append(dayPrecip.sum().multiply(precipScale)\
          .set('system:time_start',newDate.millis()))
    return ee.ImageCollection(imgList)


def calcInitIap(collection,startDate,pastDays):
    off = pastDays*-1
    s = startDate.advance(off,'day')
    e = s.advance(pastDays,'day')
    prevPrecip = collection.filterDate(s,e)

    dailyPrev = accumCFS(prevPrecip,s,pastDays)

    imgList = dailyPrev.toList(pastDays)
    outList = []

    for i in range(pastDays):
        pr = ee.Image(imgList.get(i))
        antecedent = pr.multiply(ee.Image(1).divide(pastDays-i))
        outList.append(antecedent)

    Iap = ee.ImageCollection(outList).sum().rename(['Iap'])

    return Iap


class fClass(object):
    def __init__(self,feature,initCond,initTime,
                 k=0.45,Gmax=15,L=0.1,Kr=0.9,n=10,alpha=0.9):
        # set parameters to EE variables
        self.k = ee.Image(k)
        self.Gmax = ee.Image(Gmax)
        self.L = ee.Image(L)
        self.Kr = ee.Image(Kr)
        self.n = ee.Image(n)
        self.alpha = ee.Image(alpha)
        self.pArea = feature.geometry().area()
        self.initial = ee.Image(initCond)
        self.initTime = initTime
        self.pond = feature

    def forecast(self):
        # calculate volume - area/height relationship parameters
        self.Ac = self.n.multiply(self.pArea)
        self.h0 = ee.Image(1)

        pondMin = ee.Number(elv.reduceRegion(
          geometry=self.pond.geometry(),
          reducer=ee.Reducer.min(),
          scale=30
        ).get('elevation'))
        SoInit = ee.Image(0).where(elv.gte(pondMin).And(elv.lte(pondMin.add(3))),1)
        self.So = ee.Image(ee.Number(SoInit.reduceRegion(
          geometry=self.pond.geometry(),
          reducer=ee.Reducer.sum(),
          scale=30
        ).get('constant'))).multiply(900)

        # begin forecasting water area
        forecastDays = 15
        modelDate = self.initTime

        # calculate initial conditions
        A = ee.Image(self.pArea).multiply(self.initial)
        hInit = A.divide(self.So).pow(self.h0.divide(self.alpha))
        self.Vo = self.So.multiply(self.h0).divide(self.alpha.add(1))

        precipData = gfs.filterDate(modelDate,modelDate.advance(1,'hour'))\
                        .filterMetadata('forecast_hours','greater_than',0)\
                        .select(['total_precipitation_surface'],['precip'])
        dailyPrecip = accumGFS(precipData,modelDate,forecastDays)

        initIap = calcInitIap(cfs,modelDate,7)

        # set model start with t-1 forcing
        first = ee.Image(cfs.filterDate(modelDate.advance(-1,'day'),modelDate).select(['precip']).sum())\
              .multiply(ee.Image(86400).divide(ee.Image(1e3))).addBands(initIap.multiply(1000))\
              .addBands(A.multiply(hInit)).addBands(A).addBands(hInit)\
              .rename(['precip','Iap','vol','area','height']).clip(studyArea)\
              .set('system:time_start',modelDate.advance(-6,'hour').millis()).float()

        modelOut = ee.ImageCollection.fromImages(dailyPrecip.iterate(self._accumVolume,ee.List([first])))

        pondPct = modelOut.select('area').map(self._pctArea)

        ts = makeTimeSeries(pondPct.select('area'),self.pond,key='area')
        return ts

    def _accumVolume(self,img,imgList):
        # extract out forcing and state variables
        past = ee.Image(ee.List(imgList).get(-1)).clip(studyArea)
        pastIt = past.select('Iap')
        pastPr = past.select('precip')
        pastAr = past.select('area')
        #pastHt = past.select('height')
        pastVl = past.select('vol')
        nowPr = img.select('precip').clip(studyArea)
        date = ee.Date(img.get('system:time_start'))

        # change in volume model
        deltaIt = pastIt.add(pastPr).multiply(self.k)
        Gt = self.Gmax.subtract(deltaIt)
        Gt = Gt.where(Gt.lt(0),0)
        Pe = nowPr.subtract(Gt)
        Pe = Pe.where(Pe.lt(0),0)
        Qin = self.Kr.multiply(Pe).multiply(self.Ac)
        dV = nowPr.multiply(self.pArea).add(Qin).subtract(self.L.multiply(pastAr))
        # convert dV to actual volume
        volume = pastVl.add(dV).rename(['vol'])
        volume = volume.where(volume.lt(0),0)

        # empirical model for volume to area/height relationship
        ht = volume.divide(self.Vo).pow(ee.Image(1).divide(self.alpha))\
                  .divide(ee.Image(1).divide(self.h0)).rename(['height'])
        area = self.So.multiply(ht.divide(self.h0).pow(self.alpha)).rename(['area'])
        area = area.where(area.lt(0),1) # contrain area to real values

        # set state variables to output model step
        step = nowPr.addBands(deltaIt).addBands(volume).addBands(area).addBands(ht)\
                  .set('system:time_start',date.advance(6,'hour').millis())

        return ee.List(imgList).add(step.float())

    def _pctArea(self,img):
        pct = img.divide(ee.Image(self.pArea)).copyProperties(img,['system:time_start'])
        return pct#.rename('pctArea')#.where(pct.gt(1),1)



studyArea = ee.Geometry.Rectangle([-15.866, 14.193, -12.990, 16.490])
lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT')
st2 = ee.ImageCollection('COPERNICUS/S2')
ponds = ee.FeatureCollection('projects/servir-wa/services/ephemeral_water_ferlo/ferlo_ponds')
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

gfs = ee.ImageCollection('NOAA/GFS0P25')
cfs = ee.ImageCollection('NOAA/CFSV2/FOR6H').select(['Precipitation_rate_surface_6_Hour_Average'],['precip'])
elv = ee.Image('USGS/SRTMGL1_003')

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

    ts_values = makeTimeSeries(waterCollection.select('water'),selPond,key='water')
    coordinates = selPond.getInfo()['features'][0]['geometry']['coordinates']
    return ts_values,coordinates

def forecastFeature(lon,lat):

    selPond = filterPond(lon,lat)

    featureImg = ee.Image(waterCollection.filterBounds(selPond).sort('system:time_start',False).first())

    lastTime = ee.Date(featureImg.get('system:time_start'))

    pondFraction = ee.Number(featureImg.reduceRegion(ee.Reducer.mean(), selPond.geometry(), 30).get('water'))

    fModel = fClass(selPond,pondFraction,lastTime)

    ts_values = fModel.forecast()
    coordinates = selPond.getInfo()['features'][0]['geometry']['coordinates']


    return ts_values,coordinates

def getMNDWI(lon,lat,xValue,yValue):

    selPond = filterPond(lon, lat)

    mndwi_img = getClickedImage(xValue,yValue,selPond)

    return mndwi_img
