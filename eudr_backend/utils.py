import ast
import json
import uuid


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
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        # check if polygon field is empty array or empty string
        if not record.get('polygon') or record.get('polygon') in ['']:
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
                    "coordinates": [ast.literal_eval(record.get('polygon', '[]'))]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)

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


def format_geojson_data(geojson, analysis, file_id=None):
    # Ensure the GeoJSON contains features
    geojson = json.loads(geojson) if isinstance(geojson, str) else geojson
    features = geojson.get('features', [])
    if not features:
        return []

    formatted_data_list = []
    for i, feature in enumerate(features):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        # Determine if the geometry is a Polygon and extract coordinates
        is_polygon = geometry.get('type') == 'Polygon' or geometry.get(
            'type') == 'MultiPolygon'
        coordinates = geometry.get('coordinates', [])

        # make union of coordinates if it is a MultiPolygon
        if geometry.get('type') == 'MultiPolygon':
            coordinates = []
            for polygon in geometry.get('coordinates', []):
                coordinates.extend(polygon)
        else:
            coordinates = geometry.get('coordinates', [])

        latitude = coordinates[1] if not is_polygon and len(
            coordinates) > 1 else properties.get('Centroid_lat', 0.0)
        longitude = coordinates[0] if not is_polygon and len(
            coordinates) > 0 else properties.get('Centroid_lon', 0.0)
        formatted_data = {
            "remote_id": properties.get("remote_id"),
            "farmer_name": properties.get("farmer_name"),
            "farm_size": float(properties.get("farm_size", properties.get('Plot_area_ha', 0))),
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
                "is_in_protected_areas": analysis[i].get('WDPA'),
                "is_in_water_body": analysis[i].get('In_waterbody'),
                "forest_change_loss_after_2020": analysis[i].get('GFC_loss_after_2020'),
                "fire_after_2020": analysis[i].get('MODIS_fire_after_2020'),
                "radd_after_2020": analysis[i].get('RADD_after_2020'),
                "tmf_deforestation_after_2020": analysis[i].get('TMF_def_after_2020'),
                "tmf_degradation_after_2020": analysis[i].get('TMF_deg_after_2020'),
                "tmf_disturbed": analysis[i].get('TMF_disturbed'),
                "tree_cover_loss": analysis[i].get('Indicator_1_treecover'),
                "commodities": analysis[i].get('Indicator_2_commodities'),
                "disturbance_before_2020": analysis[i].get('Indicator_3_disturbance_before_2020'),
                "disturbance_after_2020": analysis[i].get('Indicator_4_disturbance_after_2020'),
                "eudr_risk_level": analysis[i].get('EUDR_risk')
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
    except Exception as e:
        return False


def reverse_polygon_points(polygon):
    reversed_polygon = [[lon, lat] for lat, lon in polygon[0]]
    return reversed_polygon


def generate_access_code():
    return str(uuid.uuid4())
