# import ee
# import folium
# import geemap.foliumap as geemap
# from django.http import JsonResponse
# from django.utils import timezone
# import requests
# from shapely import Polygon
# from eudr_backend.utils import flatten_multipolygon_coordinates, is_valid_polygon, reverse_polygon_points
# from eudr_backend.settings import initialize_earth_engine
# from my_eudr_app.ee_images import combine_commodities_images, combine_disturbances_after_2020_images, combine_disturbances_before_2020_images, combine_forest_cover_images
# from eudr_backend.models import EUDRSharedMapAccessCodeModel
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def map_view(request):
#     fileId = request.GET.get('file-id')
#     accessCode = request.GET.get('access-code')
#     farmId = request.GET.get('farm-id')
#     http_referer = request.META.get('HTTP_REFERER')
#     overLap = http_referer and 'overlaps' in http_referer.split('/')[-1]
#     userLat = request.GET.get('lat') or 0.0
#     userLon = request.GET.get('lon') or 0.0
#     farmId = int(farmId) if farmId else None

#     if accessCode:
#         try:
#             access_record = EUDRSharedMapAccessCodeModel.objects.get(
#                 file_id=fileId, access_code=accessCode)
#             if access_record.valid_until and (access_record.valid_until < timezone.now()):
#                 return JsonResponse({"message": "Access Code Expired", "status": 403}, status=403)
#         except BaseException:
#             return JsonResponse(
#                 {"message": "Invalid file ID or access code.", "status": 403}, status=403)

#     initialize_earth_engine()

#     # Create a Folium map object.
#     m = folium.Map(location=[userLat, userLon],
#                    zoom_start=12, control_scale=True, tiles=None)

#     # Add base layers.
#     folium.TileLayer(
#         tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}', attr='Google', name='Google Maps').add_to(m)
#     folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
#                      attr='Google', name='Google Satellite', show=False).add_to(m)

#     # Fetch protected areas
#     wdpa_poly = ee.FeatureCollection("WCMC/WDPA/current/polygons")

#     wdpa_filt = wdpa_poly.filter(
#         ee.Filter.And(ee.Filter.neq('STATUS', 'Proposed'),
#                       ee.Filter.neq('STATUS', 'Not Reported'),
#                       ee.Filter.neq('DESIG_ENG', 'UNESCO-MAB Biosphere Reserve'))
#     )
#     protected_areas = ee.Image().paint(wdpa_filt, 1)

#     try:
#         # Fetch data from the RESTful API endpoint.
#         base_url = f"{request.scheme}://{request.get_host()}"
#         response = requests.get(f"""{base_url}/api/farm/map/list/""", headers={'Authorization': f"Token {request.user.auth_token}"}) if not fileId and not farmId else requests.get(f"""{base_url}/api/farm/list/{farmId}""", headers={'Authorization': f"Token {request.user.auth_token}"}) if farmId else requests.get(
#             f"""{base_url}/api/farm/list/file/{fileId}/""", headers={'Authorization': f"Token {request.user.auth_token}"}) if not overLap else requests.get(f"""{base_url}/api/farm/overlapping/{fileId}/""", headers={'Authorization': f"Token {request.user.auth_token}"})
#         if response.status_code == 200:
#             farms = [response.json()] if farmId else response.json()
#             if len(farms) > 0:
#                 # Try to get the cached tile layers
#                 high_risk_tile_layer = None
#                 # cache.get(high_risk_tile_cache_key)
#                 low_risk_tile_layer = None
#                 # cache.get(low_risk_tile_cache_key)
#                 more_info_needed_tile_layer = None
#                 # cache.get(
#                 #     more_info_needed_tile_cache_key)

#                 high_risk_farms = ee.FeatureCollection([
#                     ee.Feature(
#                         ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
#                         else ee.Geometry.Polygon(farm['polygon']),
#                         {
#                             'color': "#F64468",  # Border color
#                         }
#                     )
#                     for farm in farms if farm['analysis']['eudr_risk_level'] == 'high'
#                 ])

#                 # Low-risk farms with border and low-opacity background
#                 low_risk_farms = ee.FeatureCollection([
#                     ee.Feature(
#                         ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
#                         else ee.Geometry.Polygon(farm['polygon']),
#                         {
#                             'color': "#3AD190",  # Border color
#                         }
#                     )
#                     for farm in farms if farm['analysis']['eudr_risk_level'] == 'low'
#                 ])

#                 # Farms needing more information with border and low-opacity background
#                 more_info_needed_farms = ee.FeatureCollection([
#                     ee.Feature(
#                         ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
#                         else ee.Geometry.Polygon(farm['polygon']),
#                         {
#                             'color': "#ACDCE8",  # Border color
#                         }
#                     )
#                     for farm in farms if farm['analysis']['eudr_risk_level'] == 'more_info_needed'
#                 ])

#                 # If any of the tile layers are not cached, create and cache them
#                 if not high_risk_tile_layer:
#                     high_risk_layer = ee.Image().paint(
#                         # Paint the fill (1) and the border width (2)
#                         high_risk_farms, 1, 2
#                     )

#                     # Add the layer with low-opacity fill and a solid border color
#                     high_risk_tile_layer = geemap.ee_tile_layer(
#                         high_risk_layer,
#                         # add the fill color and border color
#                         {'palette': ["#F64468"]},
#                         'EUDR Risk Level (High)',
#                         shown=True
#                     )
#                     # cache.set(high_risk_tile_cache_key, high_risk_tile_layer, timeout=3600)  # Cache for 1 hour

#                 if not low_risk_tile_layer:
#                     low_risk_layer = ee.Image().paint(low_risk_farms, 1, 2)
#                     low_risk_tile_layer = geemap.ee_tile_layer(
#                         low_risk_layer, {'palette': ["#3AD190"]}, 'EUDR Risk Level (Low)', shown=True)
#                     # cache.set(low_risk_tile_cache_key, low_risk_tile_layer, timeout=3600)

#                 if not more_info_needed_tile_layer:
#                     more_info_needed_layer = ee.Image().paint(more_info_needed_farms, 1, 2)
#                     more_info_needed_tile_layer = geemap.ee_tile_layer(
#                         more_info_needed_layer, {'palette': ["#ACDCE8"]}, 'EUDR Risk Level (More Info Needed)', shown=True)
#                     # cache.set(more_info_needed_tile_cache_key, more_info_needed_tile_layer, timeout=3600)

#                 # Add the high risk level farms to the map
#                 m.add_child(high_risk_tile_layer)

#                 # Add the low risk level farms to the map
#                 m.add_child(low_risk_tile_layer)

#                 # Add the more info needed farms to the map
#                 m.add_child(more_info_needed_tile_layer)

#                 for farm in farms:
#                     # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
#                     polygon = flatten_multipolygon_coordinates(
#                         farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']
#                     if 'polygon' in farm and len(polygon) == 1:
#                         polygon = flatten_multipolygon_coordinates(
#                             farm['polygon'])

#                         if farm['polygon_type'] != 'Point':
#                             farm_polygon = Polygon(polygon[0])
#                             try:
#                                 is_overlapping = any(farm_polygon.overlaps(
#                                     Polygon(other_farm['polygon'][0])) for other_farm in farms)
#                             except BaseException as e:
#                                 is_overlapping = False

#                             # Define GeoJSON data for Folium
#                             js = {
#                                 "type": "FeatureCollection",
#                                 "features": [
#                                     {
#                                         "type": "Feature",
#                                         "properties": {},
#                                         "geometry": {
#                                             "coordinates": polygon,
#                                             "type": "Polygon"
#                                         }
#                                     }
#                                 ]
#                             }

#                             # If overlapping, change the fill color
#                             fill_color = '#800080' if is_overlapping else '#777'

#                             # Create the GeoJson object with the appropriate style
#                             geo_pol = folium.GeoJson(
#                                 data=js,
#                                 control=False,
#                                 style_function=lambda x, fill_color=fill_color: {
#                                     'color': 'transparent',
#                                     'fillColor': fill_color
#                                 }
#                             )
#                             folium.Popup(
#                                 html=f"""
#                     <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Plot Info</div>
#                     <div class='d-flex justify-content-between mb-2'><b>GeoID:</b> <span class='align-self-end'>{farm['geoid']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farmer Name:</b> <span class='align-self-end'>{farm['farmer_name']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farm Size:</b> <span class='align-self-end'>{farm['farm_size']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Collection Site:</b> <span class='align-self-end'>{farm['collection_site']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Agent Name:</b> <span class='align-self-end'>{farm['agent_name']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farm Village:</b> <span class='align-self-end'>{farm['farm_village']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>District:</b> <span class='align-self-end'>{farm['farm_district']}</span></div>
#                 {'<b>N.B:</b> <i>This is a Multi Polygon Type Plot</i>' if farm['polygon_type'] == 'MultiPolygon' else ''}
#                 <br><br>
#                 <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Farm Analysis</div>
#                 {
#                                     "".join([
#                                         f"<div class='d-flex justify-content-between mb-2'><b>{
#                                             key.replace('_', ' ').capitalize()}:</b> "
#                                         f"<span class='align-self-end'>"
#                                         f"{f'<span class=\"rounded px-2 py-1 text-white' + (' bg-success' if value.lower() == 'low' else ' bg-danger' if value.lower(
#                                         ) == 'high' else ' bg-info') + '\">' + value.title().replace('_', ' ') + '</span>' if key == 'eudr_risk_level' else str(value).replace('_', ' ').title() if value else '-'}"
#                                         f"</span></div>"
#                                         for key, value in farm['analysis'].items()
#                                     ])
#                                 }
#                 """, min_width="300", max_width="500").add_to(geo_pol)
#                             geo_pol.add_to(m)
#                     else:
#                         folium.Marker(
#                             location=[farm['latitude'], farm['longitude']],
#                             popup=folium.Popup(html=f"""
#                 <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Plot Info</div>
#                     <div class='d-flex justify-content-between mb-2'><b>GeoID:</b> <span class='align-self-end'>{farm['geoid']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farmer Name:</b> <span class='align-self-end'>{farm['farmer_name']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farm Size:</b> <span class='align-self-end'>{farm['farm_size']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Collection Site:</b> <span class='align-self-end'>{farm['collection_site']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Agent Name:</b> <span class='align-self-end'>{farm['agent_name']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>Farm Village:</b> <span class='align-self-end'>{farm['farm_village']}</span></div>
#                     <div class='d-flex justify-content-between mb-2'><b>District:</b> <span class='align-self-end'>{farm['farm_district']}</span></div>
#                 <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Farm Analysis</div>
#                 {
#                                 "".join([
#                                     f"<div class='d-flex justify-content-between mb-2'><b>{
#                                         key.replace('_', ' ').capitalize()}:</b> "
#                                     f"<span class='align-self-end'>"
#                                     f"{f'<span class=\"rounded px-2 py-1 text-white' + (' bg-success' if value.lower() == 'low' else ' bg-danger' if value.lower(
#                                     ) == 'high' else ' bg-info') + '\">' + value.title().replace('_', ' ') + '</span>' if key == 'eudr_risk_level' else str(value).replace('_', ' ').title() if value else '-'}"
#                                     f"</span></div>"
#                                     for key, value in farm['analysis'].items()
#                                 ])
#                             }
#                 """, min_width="300", max_width="500", show=True if farmId or (not farmId and farms.index(farm) == 0) else False
#                             ),
#                             icon=folium.Icon(color='green' if farm['analysis']['eudr_risk_level'] ==
#                                              'low' else 'red' if farm['analysis']['eudr_risk_level'] == 'high' else 'lightblue', icon='leaf'),
#                         ).add_to(m)

#                 # zoom to the extent of the map to the first polygon
#                 has_polygon = next(
#                     ((flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) for farm in farms if farm['id'] == farmId and not (flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) or not len(flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) == 2), None)
#                 if has_polygon:
#                     m.fit_bounds([reverse_polygon_points(has_polygon)],
#                                  max_zoom=18 if not farmId else 16)
#                 else:
#                     m.fit_bounds(
#                         [[farms[0]['latitude'], farms[0]['longitude']]], max_zoom=18)
#         else:
#             print("Failed to fetch data from the API")
#     except BaseException:
#         return JsonResponse({"message": "Failed to fetch data from the API"}, status=500)
#     except Exception as e:
#         return JsonResponse({"message": "An error occurred"}, status=500)

#     # Add protected areas layer
#     protected_areas_vis = {'palette': ['#585858']}
#     protected_areas_map = geemap.ee_tile_layer(
#         protected_areas, protected_areas_vis, 'Protected Areas', shown=False)
#     m.add_child(protected_areas_map)

#     # Add forest mapped areas from ee_images.py
#     forest_mapped_areas_map = geemap.ee_tile_layer(
#         combine_forest_cover_images(), {}, 'Forest Mapped Areas', shown=False)
#     m.add_child(forest_mapped_areas_map)

#     # Add commodity areas from ee_images.py
#     commodity_areas_map = geemap.ee_tile_layer(
#         combine_commodities_images(), {}, 'Commodity Areas', shown=False)
#     m.add_child(commodity_areas_map)

#     # add disturbed areas before 2020
#     disturbed_areas_before_2020_map = geemap.ee_tile_layer(
#         combine_disturbances_before_2020_images(), {}, 'Disturbed Areas Before 2020', shown=False)
#     m.add_child(disturbed_areas_before_2020_map)

#     # add disturbed areas after 2020
#     disturbed_areas_after_2020_map = geemap.ee_tile_layer(
#         combine_disturbances_after_2020_images(), {}, 'Disturbed Areas After 2020', shown=False)
#     m.add_child(disturbed_areas_after_2020_map)

#     # Add layer control
#     folium.LayerControl(collapsed=False).add_to(m)

#     # Add legend
#     legend_html = f"""
#     <div style="position: fixed;
#                 bottom: 180px; right: 10px; width: 250px; height: auto;
#                 margin-bottom: 10px;
#                 background-color: white; z-index:9999; font-size:14px;
#                 border:2px solid grey; padding: 10px;">
#     <h4>Legend</h4><br/>
#     <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #3AD190; width: 10px; height: 10px; border-radius: 30px;"></div>Low Risk Plots</div>
#     <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #F64468; width: 10px; height: 10px; border-radius: 30px;"></div>High Risk Plots</div>
#     <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #ACDCE8; width: 10px; height: 10px; border-radius: 30px;"></div>More Info Needed Plots</div>
#     <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #C3C6CF; width: 10px; height: 10px; border-radius: 30px;"></div>OverLapping Plots</div>
#     <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #585858; width: 10px; height: 10px; border-radius: 30px;"></div>Protected Areas (2021-2023)</div>
#     </div>
#     """
#     m.get_root().html.add_child(folium.Element(legend_html))

#     # Generate map HTML
#     map_html = m._repr_html_()

#     return JsonResponse({'map_html': map_html}, status=200)


import ee
import folium
import geemap.foliumap as geemap
from django.http import JsonResponse
from django.utils import timezone
import requests
from shapely import Polygon
from eudr_backend.utils import flatten_multipolygon_coordinates, is_valid_polygon, reverse_polygon_points
from eudr_backend.settings import initialize_earth_engine
from my_eudr_app.ee_images import combine_commodities_images, combine_disturbances_after_2020_images, combine_disturbances_before_2020_images, combine_forest_cover_images
from eudr_backend.models import EUDRSharedMapAccessCodeModel
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def map_view(request):
    fileId = request.GET.get('file-id')
    accessCode = request.GET.get('access-code')
    farmId = request.GET.get('farm-id')
    http_referer = request.META.get('HTTP_REFERER')
    overLap = http_referer and 'overlaps' in http_referer.split('/')[-1]

    try:
        userLat = float(request.GET.get('lat') or 0.0)
    except (TypeError, ValueError):
        userLat = 0.0

    try:
        userLon = float(request.GET.get('lon') or 0.0)
    except (TypeError, ValueError):
        userLon = 0.0

    try:
        farmId = int(farmId) if farmId else None
    except (TypeError, ValueError):
        farmId = None

    # Block unauthenticated users unless they have a valid access code
    if not accessCode and not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    # Validate access code if provided
    if accessCode:
        try:
            access_record = EUDRSharedMapAccessCodeModel.objects.get(
                file_id=fileId, access_code=accessCode)
            if access_record.valid_until and (access_record.valid_until < timezone.now()):
                return JsonResponse({"message": "Access Code Expired", "status": 403}, status=403)
        except Exception:
            return JsonResponse(
                {"message": "Invalid file ID or access code.", "status": 403}, status=403)

    # Initialize Earth Engine
    try:
        initialize_earth_engine()
    except Exception as e:
        return JsonResponse({"error": f"Earth Engine initialization failed: {str(e)}"}, status=500)

    # Create a Folium map object
    m = folium.Map(location=[userLat, userLon],
                   zoom_start=12, control_scale=True, tiles=None)

    # Add base layers
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps'
    ).add_to(m)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        show=False
    ).add_to(m)

    # Fetch protected areas
    try:
        wdpa_poly = ee.FeatureCollection("WCMC/WDPA/current/polygons")
        wdpa_filt = wdpa_poly.filter(
            ee.Filter.And(
                ee.Filter.neq('STATUS', 'Proposed'),
                ee.Filter.neq('STATUS', 'Not Reported'),
                ee.Filter.neq('DESIG_ENG', 'UNESCO-MAB Biosphere Reserve')
            )
        )
        protected_areas = ee.Image().paint(wdpa_filt, 1)
    except Exception as e:
        protected_areas = None

    try:
        # Fetch data from the RESTful API endpoint
        base_url = f"{request.scheme}://{request.get_host()}"

        # Use auth token only if user is authenticated
        headers = {}
        if request.user.is_authenticated:
            headers = {'Authorization': f"Token {request.user.auth_token}"}

        if not fileId and not farmId:
            url = f"{base_url}/api/farm/map/list/"
        elif farmId:
            url = f"{base_url}/api/farm/list/{farmId}"
        elif not overLap:
            url = f"{base_url}/api/farm/list/file/{fileId}/"
        else:
            url = f"{base_url}/api/farm/overlapping/{fileId}/"

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return JsonResponse({
                "error": f"Failed to fetch farm data. API returned status {response.status_code}."
            }, status=500)

        farms = [response.json()] if farmId else response.json()

        if len(farms) > 0:
            # Build EE feature collections per risk level
            def build_ee_feature(farm, color):
                polygon = farm.get('polygon')
                if not polygon or polygon in ['[]', ''] or not is_valid_polygon(polygon):
                    geometry = ee.Geometry.Point([farm['longitude'], farm['latitude']])
                else:
                    geometry = ee.Geometry.Polygon(polygon)
                return ee.Feature(geometry, {'color': color})

            high_risk_farms = ee.FeatureCollection([
                build_ee_feature(farm, "#F64468")
                for farm in farms
                if (farm.get('analysis') or {}).get('eudr_risk_level') == 'high'
            ])

            low_risk_farms = ee.FeatureCollection([
                build_ee_feature(farm, "#3AD190")
                for farm in farms
                if (farm.get('analysis') or {}).get('eudr_risk_level') == 'low'
            ])

            more_info_needed_farms = ee.FeatureCollection([
                build_ee_feature(farm, "#ACDCE8")
                for farm in farms
                if (farm.get('analysis') or {}).get('eudr_risk_level') == 'more_info_needed'
            ])

            high_risk_layer = ee.Image().paint(high_risk_farms, 1, 2)
            high_risk_tile_layer = geemap.ee_tile_layer(
                high_risk_layer, {'palette': ["#F64468"]}, 'EUDR Risk Level (High)', shown=True)

            low_risk_layer = ee.Image().paint(low_risk_farms, 1, 2)
            low_risk_tile_layer = geemap.ee_tile_layer(
                low_risk_layer, {'palette': ["#3AD190"]}, 'EUDR Risk Level (Low)', shown=True)

            more_info_needed_layer = ee.Image().paint(more_info_needed_farms, 1, 2)
            more_info_needed_tile_layer = geemap.ee_tile_layer(
                more_info_needed_layer, {'palette': ["#ACDCE8"]}, 'EUDR Risk Level (More Info Needed)', shown=True)

            m.add_child(high_risk_tile_layer)
            m.add_child(low_risk_tile_layer)
            m.add_child(more_info_needed_tile_layer)

            def build_analysis_html(analysis):
                rows = []
                for key, value in (analysis or {}).items():
                    label = key.replace('_', ' ').capitalize()
                    if key == 'eudr_risk_level' and value:
                        v = str(value).lower()
                        badge_class = ' bg-success' if v == 'low' else ' bg-danger' if v == 'high' else ' bg-info'
                        display = str(value).title().replace('_', ' ')
                        value_html = f"<span class='rounded px-2 py-1 text-white{badge_class}'>{display}</span>"
                    else:
                        value_html = str(value).replace('_', ' ').title() if value else '-'
                    rows.append(
                        f"<div class='d-flex justify-content-between mb-2'>"
                        f"<b>{label}:</b> <span class='align-self-end'>{value_html}</span>"
                        f"</div>"
                    )
                return "".join(rows)

            def build_popup_html(farm):
                analysis_html = build_analysis_html(farm.get('analysis') or {})
                nb_html = "<b>N.B:</b> <i>This is a Multi Polygon Type Plot</i>" if farm.get('polygon_type') == 'MultiPolygon' else ''
                return f"""
                    <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Plot Info</div>
                    <div class='d-flex justify-content-between mb-2'><b>GeoID:</b> <span class='align-self-end'>{farm.get('geoid', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>Farmer Name:</b> <span class='align-self-end'>{farm.get('farmer_name', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>Farm Size:</b> <span class='align-self-end'>{farm.get('farm_size', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>Collection Site:</b> <span class='align-self-end'>{farm.get('collection_site', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>Agent Name:</b> <span class='align-self-end'>{farm.get('agent_name', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>Farm Village:</b> <span class='align-self-end'>{farm.get('farm_village', '')}</span></div>
                    <div class='d-flex justify-content-between mb-2'><b>District:</b> <span class='align-self-end'>{farm.get('farm_district', '')}</span></div>
                    {nb_html}
                    <br><br>
                    <div class='bg-dark rounded p-2 text-white fs-4 mb-2'>Farm Analysis</div>
                    {analysis_html}
                """

            for idx, farm in enumerate(farms):
                polygon = (
                    flatten_multipolygon_coordinates(farm['polygon'])
                    if farm.get('polygon_type') == 'MultiPolygon'
                    else farm.get('polygon')
                )

                popup_html = build_popup_html(farm)
                analysis = farm.get('analysis') or {}

                if polygon and isinstance(polygon, list) and len(polygon) == 1 and farm.get('polygon_type') != 'Point':
                    try:
                        farm_polygon = Polygon(polygon[0])
                        try:
                            is_overlapping = any(
                                farm_polygon.overlaps(Polygon(other_farm['polygon'][0]))
                                for other_farm in farms
                                if other_farm is not farm and other_farm.get('polygon')
                            )
                        except Exception:
                            is_overlapping = False

                        js = {
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "properties": {},
                                    "geometry": {
                                        "coordinates": polygon,
                                        "type": "Polygon"
                                    }
                                }
                            ]
                        }

                        fill_color = '#800080' if is_overlapping else '#777'

                        geo_pol = folium.GeoJson(
                            data=js,
                            control=False,
                            style_function=lambda x, fill_color=fill_color: {
                                'color': 'transparent',
                                'fillColor': fill_color
                            }
                        )
                        folium.Popup(
                            html=popup_html,
                            min_width="300",
                            max_width="500"
                        ).add_to(geo_pol)
                        geo_pol.add_to(m)

                    except Exception:
                        # Fall back to marker if polygon rendering fails
                        risk = analysis.get('eudr_risk_level', '')
                        icon_color = 'green' if risk == 'low' else 'red' if risk == 'high' else 'lightblue'
                        folium.Marker(
                            location=[farm['latitude'], farm['longitude']],
                            popup=folium.Popup(html=popup_html, min_width="300", max_width="500"),
                            icon=folium.Icon(color=icon_color, icon='leaf'),
                        ).add_to(m)
                else:
                    risk = analysis.get('eudr_risk_level', '')
                    icon_color = 'green' if risk == 'low' else 'red' if risk == 'high' else 'lightblue'
                    show_popup = bool(farmId or (not farmId and idx == 0))

                    folium.Marker(
                        location=[farm['latitude'], farm['longitude']],
                        popup=folium.Popup(
                            html=popup_html,
                            min_width="300",
                            max_width="500",
                            show=show_popup
                        ),
                        icon=folium.Icon(color=icon_color, icon='leaf'),
                    ).add_to(m)

            # Zoom to the target farm if farmId is provided
            if farmId:
                target_farm = next((f for f in farms if f.get('id') == farmId), None)
                if target_farm:
                    target_polygon = (
                        flatten_multipolygon_coordinates(target_farm['polygon'])
                        if target_farm.get('polygon_type') == 'MultiPolygon'
                        else target_farm.get('polygon')
                    )
                    if target_polygon and len(target_polygon) > 0:
                        try:
                            m.fit_bounds([reverse_polygon_points(target_polygon)], max_zoom=16)
                        except Exception:
                            m.fit_bounds([[target_farm['latitude'], target_farm['longitude']]], max_zoom=16)
                    else:
                        m.fit_bounds([[target_farm['latitude'], target_farm['longitude']]], max_zoom=16)
            else:
                # Zoom to first farm
                first_polygon = (
                    flatten_multipolygon_coordinates(farms[0]['polygon'])
                    if farms[0].get('polygon_type') == 'MultiPolygon'
                    else farms[0].get('polygon')
                )
                if first_polygon and len(first_polygon) > 0:
                    try:
                        m.fit_bounds([reverse_polygon_points(first_polygon)], max_zoom=18)
                    except Exception:
                        m.fit_bounds([[farms[0]['latitude'], farms[0]['longitude']]], max_zoom=18)
                else:
                    m.fit_bounds([[farms[0]['latitude'], farms[0]['longitude']]], max_zoom=18)

    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    # Add protected areas layer
    if protected_areas is not None:
        try:
            protected_areas_vis = {'palette': ['#585858']}
            protected_areas_map = geemap.ee_tile_layer(
                protected_areas, protected_areas_vis, 'Protected Areas', shown=False)
            m.add_child(protected_areas_map)
        except Exception:
            pass

    # Add forest mapped areas
    try:
        forest_mapped_areas_map = geemap.ee_tile_layer(
            combine_forest_cover_images(), {}, 'Forest Mapped Areas', shown=False)
        m.add_child(forest_mapped_areas_map)
    except Exception:
        pass

    # Add commodity areas
    try:
        commodity_areas_map = geemap.ee_tile_layer(
            combine_commodities_images(), {}, 'Commodity Areas', shown=False)
        m.add_child(commodity_areas_map)
    except Exception:
        pass

    # Add disturbed areas before 2020
    try:
        disturbed_areas_before_2020_map = geemap.ee_tile_layer(
            combine_disturbances_before_2020_images(), {}, 'Disturbed Areas Before 2020', shown=False)
        m.add_child(disturbed_areas_before_2020_map)
    except Exception:
        pass

    # Add disturbed areas after 2020
    try:
        disturbed_areas_after_2020_map = geemap.ee_tile_layer(
            combine_disturbances_after_2020_images(), {}, 'Disturbed Areas After 2020', shown=False)
        m.add_child(disturbed_areas_after_2020_map)
    except Exception:
        pass

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed;
                bottom: 180px; right: 10px; width: 250px; height: auto;
                margin-bottom: 10px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding: 10px;">
        <h4>Legend</h4><br/>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div style="background: #fff; border: 1px solid #3AD190; width: 10px; height: 10px; border-radius: 30px;"></div>Low Risk Plots
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div style="background: #fff; border: 1px solid #F64468; width: 10px; height: 10px; border-radius: 30px;"></div>High Risk Plots
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div style="background: #fff; border: 1px solid #ACDCE8; width: 10px; height: 10px; border-radius: 30px;"></div>More Info Needed Plots
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div style="background: #C3C6CF; width: 10px; height: 10px; border-radius: 30px;"></div>OverLapping Plots
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div style="background: #585858; width: 10px; height: 10px; border-radius: 30px;"></div>Protected Areas (2021-2023)
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Generate and return map HTML
    map_html = m._repr_html_()
    return JsonResponse({'map_html': map_html}, status=200)