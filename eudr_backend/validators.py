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
    'polygon',
    'commodity'
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
                           'commodity'
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

    # Check if required fields are present in the header
    header = data[0]
    for field in REQUIRED_FIELDS:
        if field not in header:
            errors.append(f'"{field}" is required.')
    if len(errors) > 0:
        return errors

    # Check for any invalid fields in the header
    for field in header:
        if field not in REQUIRED_FIELDS and field not in OPTIONAL_FIELDS:
            errors.append(f'"{field}" is not a valid field.')
    if len(errors) > 0:
        return errors

    # Check each record for data validation
    for i, record in enumerate(data[1:], start=1):
        record_dict = dict(zip(header, record))

        # Validate numerical fields
        if not record_dict.get('latitude'):
            record_dict['latitude'] = 0.0

        if not record_dict.get('longitude'):
            record_dict['longitude'] = 0.0
        try:
            float(record_dict['farm_size'])
        except (ValueError, KeyError):
            errors.append(f'Record {i}: "farm_size" must be a number.')

        try:
            float(record_dict['latitude'])
        except (ValueError, KeyError):
            errors.append(f'Record {i}: "latitude" must be a number.')

        try:
            float(record_dict['longitude'])
        except (ValueError, KeyError):
            errors.append(f'Record {i}: "longitude" must be a number.')

        # Validate polygon field
        try:
            polygon = record_dict.get('polygon', '')
            if polygon:
                if float(record_dict['farm_size']) >= 4 and not is_valid_polygon(json.loads(polygon)):
                    errors.append(
                        f'Record {i}: Should have valid polygon format.')
                elif not is_valid_polygon(json.loads(polygon)):
                    errors.append(
                        f'Record {i}: Should have valid polygon format.')
        except (ValueError, SyntaxError, KeyError):
            errors.append(f'Record {i}: "polygon" must be a valid list.')

    return errors


def validate_geojson(data: dict) -> bool:
    errors = []

    try:
        if data.get('type') != 'FeatureCollection':
            errors.append('Invalid GeoJSON type. Must be FeatureCollection')
        if not isinstance(data.get('features'), list):
            errors.append('Invalid GeoJSON features. Must be a list')
    except AttributeError:
        errors.append('Invalid GeoJSON. Must be a dictionary')

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
            'commodity' : str
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
