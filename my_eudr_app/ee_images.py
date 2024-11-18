from datetime import datetime
import ee

# Tree Cover/Forest Cover

# EUFO_2020:


def jrc_gfc_2020_prep():
    jrc_gfc2020_raw = ee.ImageCollection("JRC/GFC2020/V1")
    return jrc_gfc2020_raw.mosaic().rename("EUFO_2020")

# Glad Primary:


def glad_pht_prep():
    primary_ht_forests2001_raw = ee.ImageCollection(
        'UMD/GLAD/PRIMARY_HUMID_TROPICAL_FORESTS/v1')
    primary_ht_forests2001 = primary_ht_forests2001_raw.select(
        "Primary_HT_forests").mosaic().selfMask()
    gfc = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
    gfc_loss2001_2020 = gfc.select(['lossyear']).lte(20)
    return primary_ht_forests2001.where(gfc_loss2001_2020.eq(1), 0).rename("GLAD_Primary")

#  TMF_undist:


def jrc_tmf_undisturbed_prep():
    # update from https://github.com/forestdatapartnership/whisp/issues/42
    TMF_undist_2020 = ee.ImageCollection(
        "projects/JRC/TMF/v1_2023/AnnualChanges").select("Dec2020").mosaic().eq(1)
    return TMF_undist_2020.rename("TMF_undist")

#  JAXA_FNF_2020:


def jaxa_forest_prep():
    jaxa_forest_non_forest_raw = ee.ImageCollection(
        'JAXA/ALOS/PALSAR/YEARLY/FNF4')
    jaxa_forest_non_forest_2020 = jaxa_forest_non_forest_raw.filterDate(
        '2020-01-01', '2020-12-31').select('fnf').mosaic()
    return jaxa_forest_non_forest_2020.lte(2).rename("JAXA_FNF_2020")

#  GFC_TC_2020:


def glad_gfc_10pc_prep():
    gfc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    gfc_treecover2000 = gfc.select(['treecover2000'])
    gfc_loss2001_2020 = gfc.select(['lossyear']).lte(20)
    gfc_treecover2020 = gfc_treecover2000.where(gfc_loss2001_2020.eq(1), 0)
    return gfc_treecover2020.gt(10).rename("GFC_TC_2020")

#  ESA_TC_2020:


def esa_worldcover_trees_prep():
    esa_worldcover_2020_raw = ee.Image("ESA/WorldCover/v100/2020")
    esa_worldcover_trees_2020 = esa_worldcover_2020_raw.eq(95).Or(
        esa_worldcover_2020_raw.eq(10))  # get trees and mangroves
    return esa_worldcover_trees_2020.rename('ESA_TC_2020')


# combine returned ee.Image objects into a single ee.Image object
def combine_forest_cover_images():
    eufo_2020 = jrc_gfc_2020_prep()
    glad_primary = glad_pht_prep()
    tmf_undist = jrc_tmf_undisturbed_prep()
    jaxa_fnf_2020 = jaxa_forest_prep()
    gfc_tc_2020 = glad_gfc_10pc_prep()
    esa_tc_2020 = esa_worldcover_trees_prep()

    return eufo_2020.addBands(glad_primary).addBands(tmf_undist).addBands(jaxa_fnf_2020).addBands(gfc_tc_2020).addBands(esa_tc_2020)

# 2. Commodities:
# TMF_plant:


def jrc_tmf_plantation_prep():
    jrc_tmf_transitions_raw = ee.ImageCollection(
        'projects/JRC/TMF/v1_2023/TransitionMap_Subtypes')
    jrc_tmf_transitions = jrc_tmf_transitions_raw.mosaic()
    default_value = 0

    in_list_dist = [21, 22, 23, 24, 25, 26, 61, 62, 31,
                    32, 33, 63, 64, 51, 52, 53, 54, 67, 92, 93, 94]
    jrc_tmf_disturbed = jrc_tmf_transitions.remap(
        in_list_dist, [1] * len(in_list_dist), default_value).rename("TMF_disturbed")

    in_list_plnt = [81, 82, 83, 84, 85, 86]
    jrc_tmf_plantations = jrc_tmf_transitions.remap(
        in_list_plnt, [1] * len(in_list_plnt), default_value).rename("TMF_plant")

    jrc_tmf_transition = jrc_tmf_disturbed.addBands(
        jrc_tmf_plantations)
    return jrc_tmf_transition

# oil_palm_descals:


def creaf_descals_palm_prep():
    # Load the Global Oil Palm Year of Plantation image and mosaic it
    img = ee.ImageCollection(
        "projects/ee-globaloilpalm/assets/shared/GlobalOilPalm_YoP_2021").mosaic().select("minNBR_date")
    # Calculate the year of plantation and select all below and including 2020
    oil_palm_plantation_year = img.divide(365).add(1970).floor().lte(2020)
    # Create a mask for plantations in the year 2020 or earlier
    plantation_2020 = oil_palm_plantation_year.lte(2020).selfMask()
    return plantation_2020.rename("Oil_palm_Descals")

# oil_palm_FDaP:


def fdap_palm_prep():
    fdap_palm2020_model_raw = ee.ImageCollection(
        "projects/forestdatapartnership/assets/community_palm/20240312")
    # to check with Nick (increased due to false positives)
    fdap_palm = fdap_palm2020_model_raw.mosaic().gt(0.95).selfMask()
    return fdap_palm.rename("Oil_palm_FDaP")

# Cocoa_ETH:


def eth_kalischek_cocoa_prep():
    return ee.Image('projects/ee-nk-cocoa/assets/cocoa_map_threshold_065').rename("Cocoa_ETH")

# Cocoa_bnetd:


def civ_ocs2020_prep():
    return ee.Image("BNETD/land_cover/v1/2020").select("classification").eq(9).rename("Cocoa_bnetd")

# Rubber_RBGE  - from Royal Botanical Gardens of Edinburgh (RBGE) NB for 2021


def rbge_rubber_prep():
    return ee.Image('users/wangyxtina/MapRubberPaper/rRubber10m202122_perc1585DifESAdist5pxPF').unmask().rename("Rubber_RBGE")

# combine returned ee.Image objects into a single ee.Image object


def combine_commodities_images():
    tmf_plant = jrc_tmf_plantation_prep()
    oil_palm_descals = creaf_descals_palm_prep()
    oil_palm_fdap = fdap_palm_prep()
    cocoa_eth = eth_kalischek_cocoa_prep()
    cocoa_bnetd = civ_ocs2020_prep()
    rubber_rbge = rbge_rubber_prep()

    return tmf_plant.addBands(oil_palm_descals).addBands(oil_palm_fdap).addBands(cocoa_eth).addBands(cocoa_bnetd).addBands(rubber_rbge)

# 	3. Disturbances before 2020:
# TMF_deg_before_2020:


def tmf_deg_before_2020_prep():
    tmf_deg = ee.ImageCollection(
        'projects/JRC/TMF/v1_2023/DegradationYear').mosaic()
    return (tmf_deg.lte(2020)).And(tmf_deg.gte(2000)).rename("TMF_deg_before_2020")

# TMF_def_before_2020:


def tmf_def_before_2020_prep():
    tmf_def = ee.ImageCollection(
        'projects/JRC/TMF/v1_2023/DeforestationYear').mosaic()
    return (tmf_def.lte(2020)).And(tmf_def.gte(2000)).rename("TMF_def_before_2020")

# GFC_loss_before_2020:


def glad_gfc_loss_before_2020_prep():
    # Load the Global Forest Change dataset
    gfc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    gfc_loss = gfc.select(['lossyear']).lte(20).And(
        gfc.select(['treecover2000']).gt(10))
    return gfc_loss.rename("GFC_loss_before_2020")

# ESA_fire_before_2020:


def esa_fire_before_2020_prep():
    esa_fire = ee.ImageCollection("ESA/CCI/FireCCI/5_1")
    start_year = 2000
    end_year = 2020
    date_st = str(start_year) + "-01-01"
    date_ed = str(end_year) + "-12-31"
    return esa_fire.filterDate(date_st, date_ed).mosaic().select(['BurnDate']).gte(0).rename("ESA_fire_before_2020")

# MODIS_fire_before_2020:


def modis_fire_before_2020_prep():
    modis_fire = ee.ImageCollection("MODIS/061/MCD64A1")
    start_year = 2000
    end_year = 2020
    date_st = str(start_year) + "-01-01"
    date_ed = str(end_year) + "-12-31"
    return modis_fire.filterDate(date_st, date_ed).mosaic().select(['BurnDate']).gte(0).rename("MODIS_fire_before_2020")

# RADD_before_2020:


def radd_before_2020_prep():
    from datetime import datetime
    radd = ee.ImageCollection('projects/radar-wur/raddalert/v1')

    radd_date = radd.filterMetadata(
        'layer', 'contains', 'alert').select('Date').mosaic()
    # date of availability
    # (starts 2019 in Africa, then 2020 for S America and Asia: https://data.globalforestwatch.org/datasets/gfw::deforestation-alerts-radd/about)
    start_year = 19

    # current_year = datetime.now().year % 100 # NB the % 100 part gets last two digits needed

    start = start_year*1000
    end = 20*1000+365
    return radd_date.updateMask(radd_date.gte(start)).updateMask(radd_date.lte(end)).gt(0).rename("RADD_before_2020")

# combine returned ee.Image objects into a single ee.Image object


def combine_disturbances_before_2020_images():
    tmf_deg_before_2020 = tmf_deg_before_2020_prep()
    tmf_def_before_2020 = tmf_def_before_2020_prep()
    gfc_loss_before_2020 = glad_gfc_loss_before_2020_prep()
    esa_fire_before_2020 = esa_fire_before_2020_prep()
    modis_fire_before_2020 = modis_fire_before_2020_prep()
    radd_before_2020 = radd_before_2020_prep()

    return tmf_deg_before_2020.addBands(tmf_def_before_2020).addBands(gfc_loss_before_2020).addBands(esa_fire_before_2020).addBands(modis_fire_before_2020).addBands(radd_before_2020)

# 4. Disturbances After 2020:
# TMF_deg_after_2020:


def tmf_deg_after_2020_prep():
    tmf_deg = ee.ImageCollection(
        'projects/JRC/TMF/v1_2023/DegradationYear').mosaic()
    return tmf_deg.gt(2020).rename("TMF_deg_after_2020")

# TMF_def_after_2020:


def tmf_def_after_2020_prep():
    tmf_def = ee.ImageCollection(
        'projects/JRC/TMF/v1_2023/DeforestationYear').mosaic()
    return tmf_def.gt(2020).rename("TMF_def_after_2020")

# GFC_loss_after_2020:


def glad_gfc_loss_after_2020_prep():
    # Load the Global Forest Change dataset
    gfc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    gfc_loss = gfc.select(['lossyear']).gt(20).And(
        gfc.select(['treecover2000']).gt(10)).selfMask()
    return gfc_loss.rename("GFC_loss_after_2020")

# MODIS_fire_after_2020:


def modis_fire_after_2020_prep():
    modis_fire = ee.ImageCollection("MODIS/061/MCD64A1")
    start_year = 2021
    end_year = datetime.now().year
    date_st = str(start_year) + "-01-01"
    date_ed = str(end_year) + "-12-31"
    return modis_fire.filterDate(date_st, date_ed).mosaic().select(['BurnDate']).gte(0).rename("MODIS_fire_after_2020")

# RADD_after_2020:


def radd_after_2020_prep():
    from datetime import datetime
    radd = ee.ImageCollection('projects/radar-wur/raddalert/v1')

    radd_date = radd.filterMetadata(
        'layer', 'contains', 'alert').select('Date').mosaic()
    # date of availability
    # (starts 2019 in Africa, then 2020 for S America and Asia: https://data.globalforestwatch.org/datasets/gfw::deforestation-alerts-radd/about)
    start_year = 21

    # NB the % 100 part gets last two digits needed
    current_year = datetime.now().year % 100
    start = start_year*1000
    end = current_year*1000+365
    return radd_date.updateMask(radd_date.gte(start)).updateMask(radd_date.lte(end)).gt(0).rename("RADD_after_2020")

# combine returned ee.Image objects into a single ee.Image object


def combine_disturbances_after_2020_images():
    tmf_deg_after_2020 = tmf_deg_after_2020_prep()
    tmf_def_after_2020 = tmf_def_after_2020_prep()
    gfc_loss_after_2020 = glad_gfc_loss_after_2020_prep()
    modis_fire_after_2020 = modis_fire_after_2020_prep()
    radd_after_2020 = radd_after_2020_prep()

    return tmf_deg_after_2020.addBands(tmf_def_after_2020).addBands(gfc_loss_after_2020).addBands(modis_fire_after_2020).addBands(radd_after_2020)
