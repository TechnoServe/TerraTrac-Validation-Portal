import json
from eudr_backend.utils import is_valid_polygon


REQUIRED_FIELDS = [
    'farmer_name',
    'farm_size',
    'collection_site',
    'farm_district',
    'farm_village',
    'latitude',
    'longitude',
    'polygon'
]

OPTIONAL_FIELDS = [
    'remote_id',
    'member_id',
    'agent_name',
    'created_at',
    'updated_at',
    'accuracyArray',
    'accuracies'
]

GEOJSON_REQUIRED_FIELDS = ['geometry',
                           'farmer_name',
                           'farm_size',
                           'collection_site',
                           'farm_district',
                           'farm_village',
                           'latitude',
                           'longitude',
                           ]


def validate_csv(data):
    errors = []

    # Check if required fields are present
    for field in REQUIRED_FIELDS:
        if field not in data[0]:
            errors.append(f'"{field}" is required.')
    if len(errors) > 0:
        return errors

    # Check if optional fields are present
    for field in data[0]:
        if field not in REQUIRED_FIELDS and field not in OPTIONAL_FIELDS:
            errors.append(f'"{field}" is not a valid field.')
    if len(errors) > 0:
        return errors

    # Check if farm_size, latitude, and longitude are numbers and polygon is a list
    for i, record in enumerate(
        data[:-1] if (
            len(data[-1]) < len(REQUIRED_FIELDS)
        ) else data
    ):
        try:
            float(record['farm_size'])
        except ValueError:
            errors.append(f'Record {i+1}: "farm_size" must be a number.')
        try:
            float(record['latitude'])
        except ValueError:
            errors.append(f'Record {i+1}: "latitude" must be a number.')
        try:
            float(record['longitude'])
        except ValueError:
            errors.append(f'Record {i+1}: "longitude" must be a number.')

    # if polygon is invalid, return error
    for i, record in enumerate(
        data[:-1] if (
            len(data[-1]) < len(REQUIRED_FIELDS)
        ) else data
    ):
        try:
            polygon = record['polygon']
            if float(record['farm_size']) >= 4 and not is_valid_polygon(json.loads(polygon)):
                errors.append(
                    f'Record {i+1}: Should have valid polygon format.')
            elif polygon and not is_valid_polygon(json.loads(polygon)):
                errors.append(
                    f'Record {i+1}: Should have valid polygon format.')
        except ValueError:
            errors.append(f'Record {i+1}: "polygon" must be a list.')
        except SyntaxError:
            errors.append(f'Record {i+1}: "polygon" must be a list.')

    return errors


def validate_geojson(data: dict) -> bool:
    errors = []

    if data.get('type') != 'FeatureCollection':
        errors.append('Invalid GeoJSON type. Must be FeatureCollection')
    if not isinstance(data.get('features'), list):
        errors.append('Invalid GeoJSON features. Must be a list')

    if len(errors) > 0:
        return errors

    for feature in data['features']:
        if feature.get('type') != 'Feature':
            errors.append('Invalid GeoJSON feature. Must be Feature')
            continue
        properties = feature.get('properties')
        if not isinstance(properties, dict):
            errors.append('Invalid GeoJSON properties. Must be a dictionary')
            continue

        # Check for required properties
        required_properties = {
            'farmer_name': str,
            'farm_village': str,
            'farm_district': str,
            'farm_size': (int, float),
            'latitude': (int, float),
            'longitude': (int, float),
        }
        for prop, prop_type in required_properties.items():
            if not isinstance(properties.get(prop), prop_type):
                errors.append(
                    f'Invalid GeoJSON properties. Missing or invalid "{prop}"')
        if len(errors) > 0:
            return errors

        # Check for valid geometry
        geometry = feature.get('geometry')
        if not isinstance(geometry, dict):
            print(geometry)
            errors.append('Invalid GeoJSON geometry. Must be a dictionary')
            continue
        geometry_type = geometry.get('type')
        coordinates = geometry.get('coordinates')

        if geometry_type == 'Polygon':
            if not (isinstance(coordinates, list) and len(coordinates) >= 1):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists')
            if not (isinstance(coordinates[0], list) and len(coordinates[0]) >= 4):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists with at least 4 coordinates')
            if properties.get('farm_size') >= 4 and not is_valid_polygon(coordinates):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a valid polygon')
            for coord in coordinates[0]:
                if not (isinstance(coord, list) and len(coord) == 2):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with 2 coordinates')
                if not all(isinstance(c, (int, float)) for c in coord):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with numbers')
        elif geometry_type == 'Point':
            if not (isinstance(coordinates, list) and len(coordinates) == 2):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of 2 numbers')
            if not all(isinstance(c, (int, float)) for c in coordinates):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of numbers')
            if properties.get('farm_size') >= 4:
                errors.append(
                    'Invalid record. Farm size must be less than 4 hectares for a point geometry')
        elif geometry_type == 'MultiPolygon':
            if not (isinstance(coordinates, list) and len(coordinates) >= 1):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists')
            for polygon in coordinates:
                if not (isinstance(polygon, list) and len(polygon) >= 1):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists')
                if not (isinstance(polygon[0], list) and len(polygon[0]) >= 4):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with at least 4 coordinates')
                if properties.get('farm_size') >= 4 and not is_valid_polygon(polygon):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a valid polygon')
                for coord in polygon[0]:
                    if not (isinstance(coord, list) and len(coord) == 2):
                        errors.append(
                            'Invalid GeoJSON coordinates. Must be a list of lists with 2 coordinates')
                    if not all(isinstance(c, (int, float)) for c in coord):
                        errors.append(
                            'Invalid GeoJSON coordinates. Must be a list of lists with numbers')
        else:
            errors.append(
                'Invalid GeoJSON geometry type. Must be Point or Polygon')

    return errors
