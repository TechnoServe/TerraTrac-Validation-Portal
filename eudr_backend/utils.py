import ast
import csv
import json
import uuid

import boto3
import pandas as pd
import geopandas as gpd
from eudr_backend import settings
from eudr_backend.models import EUDRUploadedFilesModel


def flatten_multipolygon(multipolygon):
    """
    Flattens a MultiPolygon geometry into a Polygon by combining inner arrays of coordinates.
    """
    if multipolygon['type'] != 'MultiPolygon':
        raise ValueError("Input geometry is not a MultiPolygon")

    # Initialize an empty list to hold combined coordinates
    flattened_coordinates = []

    # Iterate through the coordinates of each polygon in the MultiPolygon
    for polygon in multipolygon['coordinates']:
        # Each polygon has a list of rings (outer boundary, inner holes), we only want to combine the outer boundaries
        for ring in polygon:
            flattened_coordinates.extend(ring)

    # Create the new Polygon geometry
    polygon = {
        "type": "Polygon",
        "coordinates": [flattened_coordinates]
    }

    return polygon


def flatten_multipolygon_coordinates(multipolygon_coords):
    flattened_coordinates = []
    for polygon in multipolygon_coords:
        flattened_coordinates.extend(polygon)
    return [flattened_coordinates]


def transform_db_data_to_geojson(data, isSyncing=False):
    features = []
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        if not record.get('polygon') or record.get('polygon') in [''] or ((len(record.get('polygon', [])) == 1 and not isinstance(record.get('polygon', [])[0], list))):
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(record['longitude']), float(record['latitude'])]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)
        else:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": ast.literal_eval(record.get('polygon', '[]')) if type(record.get('polygon', '[]')) == str else record.get('polygon', '[]')
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "generateGeoids": "true" if isSyncing else "false"
    }

    return geojson


def transform_csv_to_json(data):
    features = []

    # Assume the first element is the header (column names)
    headers = data[0]

    # Iterate over data starting from the second row (actual data)
    for row in data[1:]:
        # Create a record as a dictionary mapping headers to row values
        record = dict(zip(headers, row))

        # Ensure that latitude, longitude, and polygon fields exist
        if 'latitude' not in record or 'longitude' not in record:
            continue

        # Handle empty or missing polygon field
        if not record['polygon'] or record['polygon'] in ['']:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(record['longitude']), float(record['latitude'])]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)
        else:
            try:
                coordinates = ast.literal_eval(record['polygon'])
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coordinates]
                    },
                    "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
                }
                features.append(feature)
            except (ValueError, SyntaxError):
                # Skip record if polygon parsing fails
                continue

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson


def flatten_geojson(geojson):
    """
    Loops through a GeoJSON object and flattens any MultiPolygon geometry to Polygon.
    """
    for feature in geojson.get('features', []):
        geometry = feature.get('geometry', {})
        if geometry['type'] == 'MultiPolygon':
            # Flatten the MultiPolygon into a Polygon
            feature['geometry'] = flatten_multipolygon(geometry)
    return geojson


# def format_geojson_data(geojson, analysis, file_id=None):
#     # Ensure the GeoJSON contains features
#     geojson = json.loads(geojson) if isinstance(geojson, str) else geojson
#     features = geojson.get('features', [])
#     if not features:
#         return []

#     formatted_data_list = []
#     for i, feature in enumerate(features):
#         properties = feature.get('properties', {})
#         geometry = feature.get('geometry', {})

#         # Determine if the geometry is a Polygon and extract coordinates
#         is_polygon = geometry.get('type') == 'Polygon' or geometry.get(
#             'type') == 'MultiPolygon'
#         coordinates = geometry.get('coordinates', [])

#         # make union of coordinates if it is a MultiPolygon
#         if geometry.get('type') == 'MultiPolygon':
#             coordinates = []
#             for polygon in geometry.get('coordinates', []):
#                 coordinates.extend(polygon)
#         else:
#             coordinates = geometry.get('coordinates', [])

#         latitude = coordinates[1] if not is_polygon and len(
#             coordinates) > 1 else properties.get('Centroid_lat', 0.0)
#         longitude = coordinates[0] if not is_polygon and len(
#             coordinates) > 0 else properties.get('Centroid_lon', 0.0)
#         formatted_data = {
#             "remote_id": properties.get("remote_id"),
#             "farmer_name": properties.get("farmer_name"),
#             "farm_size": float(properties.get("farm_size", properties.get('Plot_area_ha', 0))),
#             "collection_site": properties.get("collection_site"),
#             "agent_name": properties.get("agent_name"),
#             "farm_village": properties.get("farm_village"),
#             "farm_district": properties.get("farm_district", properties.get('Admin_Level_1')),
#             "latitude": latitude,
#             "longitude": longitude,
#             "polygon": coordinates,
#             "polygon_type": geometry.get('type'),
#             "geoid": properties.get("geoid"),
#             "file_id": file_id,
#             "analysis": {
#                 "is_in_protected_areas": False,
#                 "is_in_water_body": properties.get('In_waterbody'),
#                 "forest_change_loss_after_2020": analysis[i].get('GFC_loss_after_2020'),
#                 "fire_after_2020": analysis[i].get('MODIS_fire_after_2020'),
#                 "radd_after_2020": analysis[i].get('RADD_after_2020'),
#                 "tmf_deforestation_after_2020": analysis[i].get('TMF_def_after_2020'),
#                 "tmf_degradation_after_2020": analysis[i].get('TMF_deg_after_2020'),
#                 "tmf_disturbed": analysis[i].get('TMF_disturbed'),
#                 "tree_cover_loss": analysis[i].get('Indicator_1_treecover'),
#                 "commodities": analysis[i].get('Indicator_2_commodities'),
#                 "disturbance_before_2020": analysis[i].get('Indicator_3_disturbance_before_2020'),
#                 "disturbance_after_2020": analysis[i].get('Indicator_4_disturbance_after_2020'),
#                 "eudr_risk_level": analysis[i].get('EUDR_risk')
#             }
#         }
#         formatted_data_list.append(formatted_data)

#     return formatted_data_list


def format_geojson_data(geojson, analysis, file_id=None):
    """
    Format GeoJSON data with proper field mapping and transformations
    """
    
    def transform_indicator_value(value):
        """Transform indicator yes/no values to boolean"""
        if value == 'yes':
            return True
        elif value == 'no':
            return False
        else:
            return False  # Default to False instead of None
    
    def transform_numeric_value(value, keep_zero=True):
        """Transform numeric values, optionally keeping 0 values"""
        if value is None:
            return 0 if keep_zero else None
        if isinstance(value, (int, float)):
            return value
        return 0 if keep_zero else None
    
    # Mapping of commodity to corresponding risk key
    COMMODITY_RISK_MAP = {
        "Coffee": "risk_pcrop",
        "Cocoa": "risk_pcrop",
        "Rubber": "risk_acrop",
        "Oil palm": "risk_acrop",
        "Soy": "risk_acrop",
        "Livestock": "risk_livestock",
        "Timber": "risk_timber"
    }


    def extract_risk_level_by_commodity(analysis_result, commodity):
        try:
            properties = analysis_result[0]['properties']
            commodity = properties.get("commodity", "Coffee")  # Default to 'Coffee' if missing
            risk_key = COMMODITY_RISK_MAP.get(commodity)

            if risk_key and risk_key in properties:
                return properties[risk_key]
            else:
                print(f"No risk key found for commodity: {commodity}")
                return None

        except (IndexError, KeyError, TypeError) as e:
            print(f"Error extracting risk level for {commodity}: {e}")
            return None

    
    # def derive_eudr_risk_level(properties):
    #     """Derive EUDR risk level from individual risk fields"""
    #     # risk_fields = ['risk_pcrop', 'risk_acrop', 'risk_timber']
    #     # risk_values = [properties.get(field) for field in risk_fields if properties.get(field)]
        
    #     risk_values= properties.get('risk_pcrop')
    #     # if not risk_values:
    #     #     return 'low'  # Default to 'low' instead of None

    #     print("risk value",risk_values)
            
    #     # Priority order: high > medium > low > more_info_needed
    #     if 'high' in risk_values:
    #         return 'high'
    #     elif 'medium' in risk_values:
    #         return 'medium'
    #     elif 'low' in risk_values:
    #         return 'low'
    #     elif 'more_info_needed' in risk_values:
    #         return 'more_info_needed'
    #     # else:
    #     #     return 'low'  # Default fallback

    def extract_risk_levels(analysis_result):
        try:
            properties = analysis_result[0]['properties']
            risk_keys = ['risk_pcrop', 'risk_acrop', 'risk_timber']
            
            risk_values = {}
            for key in risk_keys:
                if key in properties:
                    risk_values[key] = properties[key]
                else:
                    # Optionally skip or handle missing keys
                    risk_values[key] = None  # or simply skip adding it
            
            return risk_values  # Dictionary of actual values or None if not found

        except (IndexError, KeyError, TypeError) as e:
            print(f"Error extracting risk levels: {e}")
            return None
        
    
    risk_info = extract_risk_levels(analysis)

    # Ensure the GeoJSON contains features
    geojson = json.loads(geojson) if isinstance(geojson, str) else geojson
    features = geojson.get('features', [])
    if not features:
        return []

    formatted_data_list = []
    for i, feature in enumerate(features):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        risk_info_commodity = extract_risk_level_by_commodity( analysis, commodity=properties.get("commodity") or "Coffee",)
        print(risk_info_commodity)
        
        # # Debug: Print available property keys for first feature
        # if i == 0:
        #     print(f"Available property keys: {list(properties.keys())}")
        #     print(f"Analysis array length: {len(analysis) if analysis else 0}")

        # Determine if the geometry is a Polygon and extract coordinates
        is_polygon = geometry.get('type') == 'Polygon' or geometry.get('type') == 'MultiPolygon'
        coordinates = geometry.get('coordinates', [])

        # Handle MultiPolygon coordinates
        if geometry.get('type') == 'MultiPolygon':
            coordinates = []
            for polygon in geometry.get('coordinates', []):
                coordinates.extend(polygon)
        else:
            coordinates = geometry.get('coordinates', [])

        # Extract latitude and longitude
        latitude = coordinates[1] if not is_polygon and len(coordinates) > 1 else properties.get('Centroid_lat', 0.0)
        longitude = coordinates[0] if not is_polygon and len(coordinates) > 0 else properties.get('Centroid_lon', 0.0)
        
        # Get analysis data - prioritize analysis array, fallback to properties
        # feature_analysis = {}
        # if analysis and i < len(analysis) and analysis[i]:
        #     feature_analysis = analysis[i]
        #     # Merge properties into feature_analysis for complete data access
        #     merged_data = {**properties, **feature_analysis}
        # else:
        #     merged_data = properties
        feature_analysis = {}
        if analysis and i < len(analysis) and analysis[i]:
            feature_analysis = analysis[i]
        
        # Debug: Print analysis data for first feature
        # if i == 0 and feature_analysis:
        #     print(f"Analysis data keys: {list(feature_analysis.keys())}")
        #     print(f"Sample analysis values: {dict(list(feature_analysis.items())[:5])}")
        
        # Helper function to get value from merged data
        # def get_field_value(field_name):
        #     return merged_data.get(field_name)
        def get_field_value(field_name):
            return feature_analysis.get(field_name, properties.get(field_name))
        
        formatted_data = {
            "remote_id": properties.get("remote_id"),
            "commodity":properties.get("commodity") or "Coffee",
            "farmer_name": properties.get("farmer_name"),
            "farm_size": float(properties.get("farm_size", properties.get('Area', properties.get('Plot_area_ha', 0)))),
            "collection_site": properties.get("collection_site"),
            "agent_name": properties.get("agent_name"),
            "farm_village": properties.get("farm_village"),
            "farm_district": properties.get("farm_district", properties.get('Admin_Level_1')),
            "latitude": latitude,
            "longitude": longitude,
            "polygon": coordinates,
            "polygon_type": geometry.get('type'),
            "geoid": properties.get("geoid"),
            "file_id": file_id,
            "analysis": {
                # Protected areas - check multiple possible fields
                "is_in_protected_areas": bool(
                    get_field_value('protected_area') or 
                    get_field_value('Protected_Area') or 
                    get_field_value('IFL_2020') or
                    get_field_value('European_Primary_Forest')
                ),
                
                # Water body mapping
                "is_in_water_body": bool(get_field_value('In_waterbody')),
                
                # Forest change loss after 2020 - sum multiple sources
                "forest_change_loss_after_2020": transform_numeric_value(
                    sum(filter(None, [
                        get_field_value('GFC_loss_after_2020') or 0,
                        get_field_value('TMF_def_after_2020') or 0,
                        get_field_value('TMF_deg_after_2020') or 0
                    ]))
                ),
                
                # Fire after 2020 - use available fire data
                "fire_after_2020": transform_numeric_value(
                    get_field_value('MODIS_fire_after_2020') or 
                    get_field_value('ESA_fire_after_2020') or 0
                ),
                
                # RADD alerts after 2020
                "radd_after_2020": transform_numeric_value(
                    get_field_value('RADD_after_2020') or 0
                ),
                
                # TMF deforestation after 2020
                "tmf_deforestation_after_2020": transform_numeric_value(
                    get_field_value('TMF_def_after_2020') or 0
                ),
                
                # TMF degradation after 2020
                "tmf_degradation_after_2020": transform_numeric_value(
                    get_field_value('TMF_deg_after_2020') or 0
                ),
                
                # Tree cover loss before 2020
                "tree_cover_loss": transform_numeric_value(
                    get_field_value('GFC_loss_before_2020') or 
                    get_field_value('TMF_def_before_2020') or 0
                ),
                
                # TMF disturbed - invert TMF_undist or check disturbance indicators
                "tmf_disturbed": (
                    not bool(get_field_value('TMF_undist')) if get_field_value('TMF_undist') is not None
                    else bool(get_field_value('TMF_def_after_2020') or get_field_value('TMF_deg_after_2020'))
                ),
                
                # Commodities - from indicator field
                "commodities": transform_indicator_value(
                    get_field_value('Ind_02_commodities')
                ),
                
                # Disturbance before 2020
                "disturbance_before_2020": transform_indicator_value(
                    get_field_value('Ind_03_disturbance_before_2020')
                ),
                
                # Disturbance after 2020
                "disturbance_after_2020": transform_indicator_value(
                    get_field_value('Ind_04_disturbance_after_2020')
                ),
                
                # EUDR risk level - use available risk data
                "eudr_risk_level": (
                    # get_field_value('EUDR_risk') or 
                    # derive_eudr_risk_level(merged_data)
                    # derive_eudr_risk_level(properties) or 
                    # derive_eudr_risk_level(feature_analysis) 
                    # risk_info['risk_pcrop']
                   risk_info_commodity
                )
            }
        }
        formatted_data_list.append(formatted_data)

    return formatted_data_list



def is_valid_polygon(polygon):
    # Check if the polygon is a list and has at least 3 points, each with exactly 2 coordinates
    try:
        if isinstance(polygon, list) and (
            (len(polygon[0]) >= 3 or len(polygon) >= 3) or
            (isinstance(polygon[0], list) and len(polygon[0][0]) >= 3)
        ):
            return True
        return False
    except Exception:
        return False


def reverse_polygon_points(polygon):
    reversed_polygon = [[lon, lat] for lat, lon in polygon[0]]
    return reversed_polygon


def generate_access_code():
    return str(uuid.uuid4())


def extract_data_from_file(file, data_format):
    try:
        if data_format == 'csv':
            data = []
            decoded_file = file.read().decode('utf-8', errors='replace').splitlines()
            reader = csv.reader(decoded_file)
            for row in reader:
                data.append(row)
        elif data_format == 'geojson':
            data = gpd.read_file(file)
            # convert to geojson
            data = json.loads(data.to_json())
        else:
            raise ValueError(
                "Unsupported data format. Please use 'csv' or 'geojson'.")
        return data
    except Exception as e:
        raise e


def store_file_in_s3(file, user, file_name, is_failed=False):
    # Store the file in the AWS S3 bucket's failed directory
    if file:
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        folder = "failed" if is_failed else "processed"
        s3.upload_fileobj(
            file, 
            settings.AWS_STORAGE_BUCKET_NAME,
            f"{folder}/{user.username}_{file_name}", 
            ExtraArgs={'ACL': 'public-read'}
        )



def handle_failed_file_entry(file_serializer, file, user):
    if "id" in file_serializer.data:
        EUDRUploadedFilesModel.objects.get(
            id=file_serializer.data.get("id")).delete()
    store_file_in_s3(file, user, file_serializer.data.get('file_name'))