import ee
import folium
import geemap.foliumap as geemap
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import requests
from shapely import Polygon
from eudr_backend.utils import flatten_multipolygon_coordinates, is_valid_polygon, reverse_polygon_points
from eudr_backend.settings import initialize_earth_engine
from my_eudr_app.ee_images import combine_commodities_images, combine_disturbances_after_2020_images, combine_disturbances_before_2020_images, combine_forest_cover_images
from eudr_backend.models import EUDRSharedMapAccessCodeModel


@login_required
def map_view(request):
    fileId = request.GET.get('file-id')
    accessCode = request.GET.get('access-code')
    farmId = request.GET.get('farm-id')
    http_referer = request.META.get('HTTP_REFERER')
    overLap = http_referer and 'overlaps' in http_referer.split('/')[-1]
    userLat = request.GET.get('lat') or 0.0
    userLon = request.GET.get('lon') or 0.0
    farmId = int(farmId) if farmId else None

    if accessCode:
        try:
            access_record = EUDRSharedMapAccessCodeModel.objects.get(
                file_id=fileId, access_code=accessCode)
            if access_record.valid_until and (access_record.valid_until < timezone.now()):
                return JsonResponse({"message": "Access Code Expired", "status": 403}, status=403)
        except BaseException:
            return JsonResponse(
                {"message": "Invalid file ID or access code.", "status": 403}, status=403)

    initialize_earth_engine()

    # Create a Folium map object.
    m = folium.Map(location=[userLat, userLon],
                   zoom_start=12, control_scale=True, tiles=None)

    # Add base layers.
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}', attr='Google', name='Google Maps').add_to(m)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                     attr='Google', name='Google Satellite', show=False).add_to(m)

    # Fetch protected areas
    wdpa_poly = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    wdpa_filt = wdpa_poly.filter(
        ee.Filter.And(ee.Filter.neq('STATUS', 'Proposed'),
                      ee.Filter.neq('STATUS', 'Not Reported'),
                      ee.Filter.neq('DESIG_ENG', 'UNESCO-MAB Biosphere Reserve'))
    )
    protected_areas = ee.Image().paint(wdpa_filt, 1)

    try:
        # Fetch data from the RESTful API endpoint.
        base_url = f"{request.scheme}://{request.get_host()}"
        response = requests.get(f"""{base_url}/api/farm/map/list/""") if not fileId and not farmId else requests.get(f"""{base_url}/api/farm/list/{farmId}""") if farmId else requests.get(
            f"""{base_url}/api/farm/list/file/{fileId}/""") if not overLap else requests.get(f"""{base_url}/api/farm/overlapping/{fileId}/""")
        print(response.status_code)
        if response.status_code == 200:
            farms = [response.json()] if farmId else response.json()
            if len(farms) > 0:
                # Try to get the cached tile layers
                high_risk_tile_layer = None
                # cache.get(high_risk_tile_cache_key)
                low_risk_tile_layer = None
                # cache.get(low_risk_tile_cache_key)
                more_info_needed_tile_layer = None
                # cache.get(
                #     more_info_needed_tile_cache_key)

                high_risk_farms = ee.FeatureCollection([
                    ee.Feature(
                        ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
                        else ee.Geometry.Polygon(farm['polygon']),
                        {
                            'color': "#F64468",  # Border color
                        }
                    )
                    for farm in farms if farm['analysis']['eudr_risk_level'] == 'high'
                ])

                # Low-risk farms with border and low-opacity background
                low_risk_farms = ee.FeatureCollection([
                    ee.Feature(
                        ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
                        else ee.Geometry.Polygon(farm['polygon']),
                        {
                            'color': "#3AD190",  # Border color
                        }
                    )
                    for farm in farms if farm['analysis']['eudr_risk_level'] == 'low'
                ])

                # Farms needing more information with border and low-opacity background
                more_info_needed_farms = ee.FeatureCollection([
                    ee.Feature(
                        ee.Geometry.Point([farm['longitude'], farm['latitude']]) if not farm.get('polygon') or farm.get('polygon') in ['[]', ''] or not is_valid_polygon(farm.get('polygon'))
                        else ee.Geometry.Polygon(farm['polygon']),
                        {
                            'color': "#ACDCE8",  # Border color
                        }
                    )
                    for farm in farms if farm['analysis']['eudr_risk_level'] == 'more_info_needed'
                ])

                # If any of the tile layers are not cached, create and cache them
                if not high_risk_tile_layer:
                    high_risk_layer = ee.Image().paint(
                        # Paint the fill (1) and the border width (2)
                        high_risk_farms, 1, 2
                    )

                    # Add the layer with low-opacity fill and a solid border color
                    high_risk_tile_layer = geemap.ee_tile_layer(
                        high_risk_layer,
                        # add the fill color and border color
                        {'palette': ["#F64468"]},
                        'EUDR Risk Level (High)',
                        shown=True
                    )
                    # cache.set(high_risk_tile_cache_key, high_risk_tile_layer, timeout=3600)  # Cache for 1 hour

                if not low_risk_tile_layer:
                    low_risk_layer = ee.Image().paint(low_risk_farms, 1, 2)
                    low_risk_tile_layer = geemap.ee_tile_layer(
                        low_risk_layer, {'palette': ["#3AD190"]}, 'EUDR Risk Level (Low)', shown=True)
                    # cache.set(low_risk_tile_cache_key, low_risk_tile_layer, timeout=3600)

                if not more_info_needed_tile_layer:
                    more_info_needed_layer = ee.Image().paint(more_info_needed_farms, 1, 2)
                    more_info_needed_tile_layer = geemap.ee_tile_layer(
                        more_info_needed_layer, {'palette': ["#ACDCE8"]}, 'EUDR Risk Level (More Info Needed)', shown=True)
                    # cache.set(more_info_needed_tile_cache_key, more_info_needed_tile_layer, timeout=3600)

                # Add the high risk level farms to the map
                m.add_child(high_risk_tile_layer)

                # Add the low risk level farms to the map
                m.add_child(low_risk_tile_layer)

                # Add the more info needed farms to the map
                m.add_child(more_info_needed_tile_layer)

                for farm in farms:
                    # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
                    polygon = flatten_multipolygon_coordinates(
                        farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']
                    if 'polygon' in farm and len(polygon) == 1:
                        polygon = flatten_multipolygon_coordinates(
                            farm['polygon'])

                        if polygon:
                            farm_polygon = Polygon(polygon[0])
                            is_overlapping = any(farm_polygon.overlaps(
                                Polygon(other_farm['polygon'][0])) for other_farm in farms)

                            # Define GeoJSON data for Folium
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

                            # If overlapping, change the fill color
                            fill_color = '#800080' if is_overlapping else '#777'

                            # Create the GeoJson object with the appropriate style
                            geo_pol = folium.GeoJson(
                                data=js,
                                control=False,
                                style_function=lambda x, fill_color=fill_color: {
                                    'color': 'transparent',
                                    'fillColor': fill_color
                                }
                            )
                            folium.Popup(
                                html=f"""
                <b><i><u>Plot Info:</u></i></b><br><br>
                                <b>GeoID:</b> {farm['geoid']}<br>
                                <b>Farmer Name:</b> {farm['farmer_name']}<br>
                <b>Farm Size:</b> {farm['farm_size']}<br>
                <b>Collection Site:</b> {farm['collection_site']}<br>
                <b>Agent Name:</b> {farm['agent_name']}<br>
                <b>Farm Village:</b> {farm['farm_village']}<br>
                <b>District:</b> {farm['farm_district']}<br>
                {'<b>N.B:</b> <i>This is a Multi Polygon Type Plot</i>' if farm['polygon_type'] == 'MultiPolygon' else ''}
                <br><br>
                <b><i><u>Farm Analysis:</u></i></b><br>
                {
                                    "<br>".join([f"<b>{key.replace('_', ' ').capitalize(
                                    )}:</b> {str(value).replace('_', ' ').title() if value else 'No'}" for key, value in farm['analysis'].items()])
                                }
                """, max_width="500").add_to(geo_pol)
                            geo_pol.add_to(m)
                    else:
                        folium.Marker(
                            location=[farm['latitude'], farm['longitude']],
                            popup=folium.Popup(html=f"""
                <b><i><u>Plot Info:</u></i></b><br><br>
                                <b>GeoID:</b> {farm['geoid']}<br>
                                <b>Farmer Name:</b> {farm['farmer_name']}<br>
                <b>Farm Size:</b> {farm['farm_size']}<br>
                <b>Collection Site:</b> {farm['collection_site']}<br>
                <b>Agent Name:</b> {farm['agent_name']}<br>
                <b>Farm Village:</b> {farm['farm_village']}<br>
                <b>District:</b> {farm['farm_district']}<br><br>
                <b><i><u>Farm Analysis:</u></i></b><br>
                {
                                "<br>".join([f"<b>{key.replace('_', ' ').capitalize(
                                )}:</b> {str(value).replace('_', ' ').title() if value else 'No'}" for key, value in farm['analysis'].items()])
                            }
                """, max_width="500", show=True if farmId or (not farmId and farms.index(farm) == 0) else False
                            ),
                            icon=folium.Icon(color='green' if farm['analysis']['eudr_risk_level'] ==
                                             'low' else 'red' if farm['analysis']['eudr_risk_level'] == 'high' else 'lightblue', icon='leaf'),
                        ).add_to(m)

                # zoom to the extent of the map to the first polygon
                has_polygon = next(
                    ((flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) for farm in farms if farm['id'] == farmId and not (flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) or not len(flatten_multipolygon_coordinates(farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']) == 2), None)
                if has_polygon:
                    m.fit_bounds([reverse_polygon_points(has_polygon)],
                                 max_zoom=18 if not farmId else 16)
                else:
                    m.fit_bounds(
                        [[farms[0]['latitude'], farms[0]['longitude']]], max_zoom=18)
        else:
            print("Failed to fetch data from the API")
    except BaseException:
        return JsonResponse({"message": "Failed to fetch data from the API"}, status=500)

    # Add protected areas layer
    protected_areas_vis = {'palette': ['#585858']}
    protected_areas_map = geemap.ee_tile_layer(
        protected_areas, protected_areas_vis, 'Protected Areas', shown=False)
    m.add_child(protected_areas_map)

    # Add forest mapped areas from ee_images.py
    forest_mapped_areas_map = geemap.ee_tile_layer(
        combine_forest_cover_images(), {}, 'Forest Mapped Areas', shown=False)
    m.add_child(forest_mapped_areas_map)

    # Add commodity areas from ee_images.py
    commodity_areas_map = geemap.ee_tile_layer(
        combine_commodities_images(), {}, 'Commodity Areas', shown=False)
    m.add_child(commodity_areas_map)

    # add disturbed areas before 2020
    disturbed_areas_before_2020_map = geemap.ee_tile_layer(
        combine_disturbances_before_2020_images(), {}, 'Disturbed Areas Before 2020', shown=False)
    m.add_child(disturbed_areas_before_2020_map)

    # add disturbed areas after 2020
    disturbed_areas_after_2020_map = geemap.ee_tile_layer(
        combine_disturbances_after_2020_images(), {}, 'Disturbed Areas After 2020', shown=False)
    m.add_child(disturbed_areas_after_2020_map)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend
    legend_html = f"""
    <div style="position: fixed;
                bottom: 180px; right: 10px; width: 250px; height: auto;
                margin-bottom: 10px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding: 10px;">
    <h4>Legend</h4><br/>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #3AD190; width: 10px; height: 10px; border-radius: 30px;"></div>Low Risk Plots</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #F64468; width: 10px; height: 10px; border-radius: 30px;"></div>High Risk Plots</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #fff; border: 1px solid #ACDCE8; width: 10px; height: 10px; border-radius: 30px;"></div>More Info Needed Plots</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #C3C6CF; width: 10px; height: 10px; border-radius: 30px;"></div>OverLapping Plots</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #585858; width: 10px; height: 10px; border-radius: 30px;"></div>Protected Areas (2021-2023)</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Generate map HTML
    map_html = m._repr_html_()

    return JsonResponse({'map_html': map_html}, status=200)
