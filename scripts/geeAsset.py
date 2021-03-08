import ee
import urllib.request
import time
from ee.batch import Export

ee.Initialize()
cloudThresh = 10
shadowSumThresh = 0.35

def addArea(feature):
    return feature.set('area',feature.area());
ponds = ee.FeatureCollection('projects/servir-wa/services/ephemeral_water_ferlo/ferlo_ponds') #\
                #.map(addArea).filter(ee.Filter.gt("area",10000))
def lsTOA(img):
    return ee.Algorithms.Landsat.TOA(img)
def rescale(img, thresholds):
    return img.subtract(thresholds[0]).divide(thresholds[1] - thresholds[0])


def lsCloudMask(img):
    blank = ee.Image(0)
    scored = ee.Algorithms.Landsat.simpleCloudScore(img)
    clouds = blank.where(scored.select(['cloud']).lte(cloudThresh), 1)\
                .clip(img.geometry())
    img = img.addBands(clouds.rename(['cloudMask']))
    return img.updateMask(clouds).set("system:time_start", img.get("system:time_start"),
                   "SUN_ZENITH",ee.Number(90).subtract(img.get('SUN_ELEVATION')),
                   "scale",ee.Number(30))
				   
def simpleTDOM2(collection, zScoreThresh, shadowSumThresh, dilatePixels):
    def darkMask(img):
        zScore = img.select(shadowSumBands).subtract(irMean).divide(irStdDev)
        irSum = img.select(shadowSumBands).reduce(ee.Reducer.sum())
        TDOMMask = zScore.lt(zScoreThresh).reduce(ee.Reducer.sum()).eq(2).And(irSum.lt(shadowSumThresh)).Not()
        TDOMMask = TDOMMask.focal_min(dilatePixels)
        img = img.addBands(TDOMMask.rename(['TDOMMask']))
        # Combine the cloud and shadow masks
        combinedMask = img.select('cloudMask').mask().And(img.select('TDOMMask'))\
            .rename('cloudShadowMask');
        return img.addBands(combinedMask).updateMask(combinedMask)

    shadowSumBands = ['nir','swir1','swir2']
    irStdDev = collection.select(shadowSumBands).reduce(ee.Reducer.stdDev())
    irMean = collection.select(shadowSumBands).mean()

    collection = collection.map(darkMask)

    return collection
	
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
    score = score.multiply(100).byte().lte(cloudThresh)
    mask = score.And(qa.lt(1024)).rename(['cloudMask'])\
                .clip(img.geometry())
    img = img.addBands(mask)
    return img.divide(10000).set("system:time_start", img.get("system:time_start"),
                                 'CLOUD_COVER',img.get('CLOUD_COVERAGE_ASSESSMENT'),
                                 'SUN_AZIMUTH',img.get('MEAN_SOLAR_AZIMUTH_ANGLE'),
                                 'SUN_ZENITH',img.get('MEAN_SOLAR_ZENITH_ANGLE'),
                                 'scale',ee.Number(10))


def mergeCollections(l8, s2, studyArea, t1, t2):
    lc8rename = l8.filterBounds(studyArea).filterDate(t1, t2).map(lsTOA).filter(
        ee.Filter.lt('CLOUD_COVER', 75)).map(lsCloudMask).select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7','cloudMask'],
                                                                 ['blue', 'green', 'red', 'nir', 'swir1', 'swir2','cloudMask'])

    st2rename = s2.filterBounds(studyArea).filterDate(t1, t2).filter(
        ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', 75)).map(s2CloudMask).select(
        ['B2', 'B3', 'B4', 'B8', 'B11', 'B12','cloudMask'],
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2','cloudMask'])
		#.map(bandPassAdjustment)

    return ee.ImageCollection(lc8rename.merge(st2rename))
	
def is_connected():
    try:
        urllib.request.urlopen('https://www.google.com/', timeout=1)
        return True
    except urllib.request.URLError:
        return False

iniDate = ee.Date('2020-01-06')
today = ee.Date('2020-01-31')

endDate = ee.Date(today)
dilatePixels = 2;
zScoreThresh = -0.8;
shadowSumThresh = 0.35;

def dataPrepper(img):
    mndwi = img.expression('0.1511 * B1 + 0.1973 * B2 + 0.3283 * B3 + 0.3407 * B4 + -0.7117 * B5 + -0.4559 * B7',{
        'B1': img.select('blue'),
        'B2': img.select('green'),
        'B3': img.select('red'),
        'B4': img.select('nir'),
        'B5': img.select('swir1'),
        'B7': img.select('swir2'),
    }).rename('mndwi')
    water =  mndwi.gte(ee.Number(-0.1304)).rename("water")

    out = ee.Image.cat([
        mndwi.multiply(10000).int16(),
        water.uint8(),
    ]).set('system:time_start', img.get('system:time_start'))
    return out



# You will want to use ur features instead
geometry = ee.Geometry.Polygon([[[-15.866,14.193],
                                 [-12.990,14.193],
                                 [-12.990,16.490],
                                 [-15.866,16.490],
                                 [-15.866,14.193]]])

lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT')
st2 = ee.ImageCollection('COPERNICUS/S2')
mergedCollection = mergeCollections(lc8, st2, geometry, iniDate, endDate).sort('system:time_start', False)

mergedCollection = simpleTDOM2(mergedCollection, zScoreThresh, shadowSumThresh, dilatePixels)


collection = ee.ImageCollection(mergedCollection).filterBounds(geometry).filterDate(iniDate, endDate)
# do any other processing u can, like urs needs merging and stuff
# also create a map function to clip to the features and map ur collection to it

processedCollection =  collection.map(dataPrepper)

# then ur final processed collection u will export

wqImages = processedCollection.size().getInfo()
wqicList = processedCollection.toList(wqImages)

print(str(wqImages))

for i in range(wqImages):
    if i < 0:
        print("Skipping: " + str(i))
    else:
        try:
            print("In export loop: " + str(i))
            thisImg = ee.Image(wqicList.get(i))
            name = thisImg.get('system:index').getInfo()
            print(name)
            task = ee.batch.Export.image.toAsset(image= thisImg, description='ewf_ponds',
                                                 assetId='projects/servir-wa/services/ephemeral_water_ferlo/processed_ponds/' + name, scale=30,
                                                 maxPixels=1.0E13, region=thisImg.geometry())
            while not is_connected:
                print("No connection: sleeping")
                time.sleep(1)
            try:
                task.start()
            except:
                while not is_connected():
                    print("No connection: sleeping")
                    time.sleep(1)
                task.start()
        except Exception as e:
            print(e)
            continue

