import ee
import urllib.request
import time
from ee.batch import Export
from datetime import date
from datetime import datetime, timedelta
import json
from tethysapp.waterwatch import config

try:
    credentials = ee.ServiceAccountCredentials(config.EE_SERVICE_ACCOUNT,
                                               config.EE_SECRET_KEY)
    ee.Initialize(credentials)
except:
    ee.Initialize()


def landsatQaMask(img):
    """Custom QA masking method for Landsat surface reflectance dataset
    """
    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = 1 << 3
    cloudsBitMask = 1 << 5

    # Get the pixel QA band.
    qa = img.select('pixel_qa')

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloudShadowBitMask).eq(0)
            .And(qa.bitwiseAnd(cloudsBitMask).eq(0))
    )

    # Return the masked image, scaled to reflectance, without the QA bands.
    return (
        img.updateMask(mask).divide(10000)
            .select("B[0-9]*")
            .copyProperties(img, ["system:time_start"])
    )


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
        S2_CLOUD_PROBA_COLL
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
    return (
        img.updateMask(is_cld_shdw.Not())
            .divide(10000).select("B.*")
            .copyProperties(img, ["system:time_start"])
    )


def harmonize(s2img):
    """Function to apply and pass adjustment to S2 data
    for hamronized landsat-sentinel2 data
    """
    landsatLike = s2img.multiply(GAIN).add(BIAS)

    return landsatLike.copyProperties(s2img, ["system:time_start"])


def mergeCollections(l8, s2, studyArea, t1, t2):
    # preprocess the landsat inputs
    # spatio-temporal filter
    # inital metadata cloud filter (don't want super cloudy images)
    # apply the QA masking function on all imagery
    # rename the bands we want to use
    lc8preprocess = (
        l8.filterBounds(studyArea)
            .filterDate(t1, t2)
            .filter(ee.Filter.lt('CLOUD_COVER', 75))
            .map(landsatQaMask)
            .select(
            ['B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
            ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        )
    )

    # preprocess the sentinel2 inputs
    # use same preprocessing workflow as landsat
    # except apply band pass adjustment at the end
    st2preprocess = (
        s2.filterBounds(studyArea)
            .filterDate(t1, t2)
            .filter(ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', 75))
            .map(sentinel2QaMask)
            .select(
            ['B2', 'B3', 'B4', 'B8', 'B11', 'B12'],
            ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        )
            .map(harmonize)
    )

    return ee.ImageCollection(lc8preprocess.merge(st2preprocess))


def is_connected():
    """Function to make sure we are still connected to EE servers for
    long running processes
    """
    try:
        urllib.request.urlopen('https://www.google.com/', timeout=1)
        return True
    except urllib.request.URLError:
        return False


def gond_waterclassifier(ndvi, ndwi, swir):
    """Implementation of surface water mapping algorithm from https://www.tandfonline.com/doi/abs/10.1080/0143116031000139908
    English description here: https://www.mdpi.com/1424-8220/20/2/431/
    """

    ndDiff = ndvi.subtract(ndwi)
    ndDiffAvg = ndDiff.focal_mean(45, "square")
    diffDiff = ndDiffAvg.subtract(ndDiff)
    indexWater = diffDiff.gte(0.08)
    swirAvg = swir.focal_mean(45, "square")
    swirDiff = swirAvg.subtract(swir)
    swirWater = swirDiff.gte(0.05)

    return indexWater.And(swirWater)


def watermapping(img):
    """Function to calculate water indices and detect water using thresholds
    Result is a multi band image of water from multiple water detection methods
    """
    # calculate different indices to threshold
    # modified normalized difference water index
    mndwi = img.normalizedDifference(["green", "swir1"]).rename("mndwi")

    # normalized difference moisture index
    ndmi = img.normalizedDifference(["nir", "swir1"]).rename("ndmi")

    # automated water extraction index (no shadow)
    aweinsh = img.expression(
        "4.0 * (g-s) - ((0.25*n) + (2.75*w))",
        {
            "g": img.select("green"),
            "s": img.select("swir1"),
            "n": img.select("nir"),
            "w": img.select("swir2"),
        },
    ).rename("aewinsh")

    # automated water extraction index (shadow) 
    aweish = img.expression(
        "b+2.5*g-1.5*(n+s)-0.25*w",
        {
            "b": img.select("blue"),
            "g": img.select("green"),
            "n": img.select("nir"),
            "s": img.select("swir1"),
            "w": img.select("swir2"),
        },
    ).rename("aewish")

    # water ratio index
    wri = img.expression(
        "(green+red)/(nir+swir)",
        {
            "green": img.select("green"),
            "red": img.select("red"),
            "nir": img.select("nir"),
            "swir": img.select("swir1"),
        },
    ).rename("wri")

    # tassled cap wetness index
    twc = img.expression(
        '0.1511 * B1 + 0.1973 * B2 + 0.3283 * B3 + 0.3407 * B4 + -0.7117 * B5 + -0.4559 * B7',
        {
            'B1': img.select('blue'),
            'B2': img.select('green'),
            'B3': img.select('red'),
            'B4': img.select('nir'),
            'B5': img.select('swir1'),
            'B7': img.select('swir2'),
        }
    ).rename('tcw')

    # concatenate the indices together that will be thresholded
    indices = ee.Image.cat([
        img.select(["swir.*"]),
        mndwi,
        ndmi,
        aweinsh,
        aweish,
        wri,
        twc
    ])

    # loop through the multiple indices classify water based on threshold values
    waters = []
    for k, v in WATER_THRESHS.items():
        # check if we need to do < or > operator
        if k in ["swir1", "swir2"]:
            water_id = indices.select(k).lt(ee.Number(v))
        else:
            water_id = indices.select(k).gt(ee.Number(v))

        # append iamges to list to concatenate later
        waters.append(water_id.rename(f"{k}_water"))

    # decicion tree classification process, commented out because it takes a while to run
    # ndvi = img.normalizedDifference(["nir","red"]).rename("ndvi")
    # ndwi = img.normalizedDifference(["green","nir"]).rename("ndwi")
    # gond_water = gond_waterclassifier(ndvi,ndwi, img.select("swir1")).rename("gond_water")
    # waters.append(gond_water)

    # concatenate all of the water images together and cast to byte datatype
    # valid values should be 0 (no water) or 1 (water)
    out = (
        ee.Image.cat(waters).uint8()
            .copyProperties(img, ["system:time_start"])
    )

    return out


def process_data(geometry, asset_id, region_name):
    print("running: " + region_name + " from: " + iniDate.format('YYYY-mm-dd').getInfo() + " to " + endDate.format('YYYY-mm-dd').getInfo())
    mergedCollection = mergeCollections(LC, S2, geometry, iniDate, endDate).sort('system:time_start', False)
    # apply the multi-threshod water mapping process
    processedCollection = mergedCollection.map(watermapping)
    # get some info for exports
    wqImages = processedCollection.size().getInfo()
    wqicList = processedCollection.toList(wqImages)
    print(f"Attemping to export {wqImages} images...")
    # loop through the imagery to export
    for i in range(wqImages):
        if i < 0:
            print("Skipping: " + str(i))
        else:
            try:
                print("In export loop: " + str(i))
                thisImg = ee.Image(wqicList.get(i))
                name = thisImg.get('system:index').getInfo()
                outScale = 30 if "LC08" in name else 10
                print(f"Image name:{name}")
                task = ee.batch.Export.image.toAsset(image=thisImg, description='ewf_ponds',
                                                     assetId=asset_id + name,
                                                     scale=outScale,
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


# sentinel2 band pass adjustment coefficients
# coeffs taken from https://www.sciencedirect.com/science/article/pii/S0034425718304139
GAIN = ee.Image.constant([0.9778, 1.0053, 0.9765, 0.9983, 0.9987, 1.003])
BIAS = ee.Image.constant([-0.00411, -0.00093, 0.00094, -0.0001, -0.0015, -0.0012])

# sentinel2 cloud probability collection
# used in S2 QA process
S2_CLOUD_PROBA_COLL = ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")

# define the Landat and Sentinel2 surface reflectance products
LC8_1 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')
LC8_2 = ee.ImageCollection('LANDSAT/LC08/C01/T2_SR')
LC = ee.ImageCollection(LC8_1.merge(LC8_2))
S2 = ee.ImageCollection('COPERNICUS/S2_SR')

# dictionary containing the threshold for different water indices
# used for multi thresholding water bodies based on index
# thresholds taken from https://www.mdpi.com/1424-8220/20/2/431/
# only use indices/thresholds from table 5 with OA over 90%
WATER_THRESHS = {
    "swir1": 0.2522,
    "swir2": 0.1652,
    "ndmi": 0.0149,
    "mndwi": -0.3350,
    "wri": 0.6250,
    "tcw": -0.1118,
    "aewish": -0.4078,
    "aewinsh": -1.3835,
}

f = open('/home/tethys/apps/WaterWatch/scripts/region_info.json')

# returns JSON object as
# a dictionary
region_info = json.load(f)

f.close()

# change dates to range to process
iniDate = ee.Date((datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d'))  # 1 week prior

endDate = ee.Date(ee.Date(datetime.today().strftime('%Y-%m-%d')))  # today

for region in region_info["regions"]:
    process_data(ee.Geometry.Polygon(region['geometry']), region['gee_asset_id'], region['name'])

# preprocess and merge the landsat8 and sentinel2 data for a spatial/temporal domain
