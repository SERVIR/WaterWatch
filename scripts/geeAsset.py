import ee
import urllib.request
import time
from ee.batch import Export

ee.Initialize()


def landsatQaMask(img):
    """Custom QA masking method for Landsat surface reflectance dataset
    """
    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = 1 << 3
    cloudsBitMask = 1 << 5

    # Get the pixel QA band.
    qa = image.select('pixel_qa')

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloudShadowBitMask).eq(0)
        .And(qa.bitwiseAnd(cloudsBitMask).eq(0))
    )

    # Return the masked image, scaled to reflectance, without the QA bands.
    return image.updateMask(mask).divide(10000)
        .select("B[0-9]*")
        .copyProperties(image, ["system:time_start"]);

def sentinel2QaMask(img):
    """Custom QA masking method for Sentinel2 L1C/S2A dataset
    """
    # set some constant variables for the S2 cloud masking
    CLD_PRB_THRESH = 40
    NIR_DRK_THRESH = 0.175 * 1e4
    CLD_PRJ_DIST = 3
    BUFFER = 100
    CRS = img.select(0).projection()

    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(
        s2_cld_prb_coll
        .filter(ee.Filter.eq("system:index", img.get("system:index")))
        .first()
    ).select("probability")

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH)

    # Identify water pixels from the SCL band, invert.
    not_water = img.select("SCL").neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    dark_pixels = img.select("B8").lt(NIR_DRK_THRESH).multiply(not_water)

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(
        ee.Number(img.get("MEAN_SOLAR_AZIMUTH_ANGLE"))
    )

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (
        is_cloud.directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST * 10)
        .reproject(**{"crs": CRS, "scale": 120})
        .select("distance")
        .mask()
    )

    # Identify the intersection of dark pixels with cloud shadow projection.
    is_shadow = cld_proj.multiply(dark_pixels)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = is_cloud.add(is_shadow).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (
        is_cld_shdw.focal_min(2)
        .focal_max(BUFFER * 2 / 20)
        .reproject(**{"crs": CRS, "scale": 60})
        .rename("cloudmask")
    )

    # Subset reflectance bands and update their masks, return the result.
    return img.select("B.*").updateMask(is_cld_shdw.Not())


def addArea(feature):
    return feature.set('area',feature.area());
ponds = ee.FeatureCollection('projects/servir-wa/services/ephemeral_water_ferlo/ferlo_ponds') #\
                #.map(addArea).filter(ee.Filter.gt("area",10000))
def lsTOA(img):
    return ee.Algorithms.Landsat.TOA(img)

def mergeCollections(l8, s2, studyArea, t1, t2):
    lc8rename = l8.filterBounds(studyArea).filterDate(t1, t2).map(lsTOA).filter(
        ee.Filter.lt('CLOUD_COVER', 75)).map(landsatQaMask).select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7','cloudMask'],
                                                                 ['blue', 'green', 'red', 'nir', 'swir1', 'swir2','cloudMask'])

    st2rename = s2.filterBounds(studyArea).filterDate(t1, t2).filter(
        ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', 75)).map(sentinel2QaMask).select(
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



s2_cld_prb_coll = (
    ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")
    .filterDate(iniDate,endtoday)
)

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

