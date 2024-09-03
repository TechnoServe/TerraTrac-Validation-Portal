from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import ee
import folium
import geemap.foliumap as geemap
import requests
from eudr_backend.settings import initialize_earth_engine


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


@login_required
def index(request):
    active_page = "index"

    return render(request, "index.html", {"active_page": active_page, 'user': request.user})


@login_required
def validator(request):
    active_page = "validator"

    return render(request, "validator.html", {"active_page": active_page, 'user': request.user})


@login_required
def validated_files(request):
    active_page = "validated_files"

    return render(request, "validated_files.html", {"active_page": active_page, 'user': request.user})


@login_required
def map(request):
    active_page = "map"

    return render(request, "map.html", {"active_page": active_page, 'user': request.user})


@login_required
def users(request):
    active_page = "users"

    return render(request, "users.html", {"active_page": active_page, 'user': request.user})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')


@login_required
def map_view(request):
    initialize_earth_engine()
    fileId = request.GET.get('file-id')
    farmId = request.GET.get('farm-id')
    userLat = request.GET.get('lat') or 0.0
    userLon = request.GET.get('lon') or 0.0
    farmId = int(farmId) if farmId else None

    # Create a Folium map object.
    m = folium.Map(location=[userLat, userLon],
                   zoom_start=12, control_scale=True, tiles=None)

    # Add base layers.
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}', attr='Google', name='Google Maps').add_to(m)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                     attr='Google', name='Google Satellite', show=False).add_to(m)

    # Add deforestation layer (2021-2023)
    gfc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    deforestation = gfc.select(['lossyear']).gt(
        20).And(gfc.select(['treecover2000']).gt(10))
    # Fetch protected areas
    wdpa_poly = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    wdpa_filt = wdpa_poly.filter(
        ee.Filter.And(ee.Filter.neq('STATUS', 'Proposed'),
                      ee.Filter.neq('STATUS', 'Not Reported'),
                      ee.Filter.neq('DESIG_ENG', 'UNESCO-MAB Biosphere Reserve'))
    )
    protected_areas = ee.Image().paint(wdpa_filt, 1)

    # kbas_2023_poly = ee.FeatureCollection("projects/ee-andyarnellgee/assets/p0004_commodity_mapper_support/raw/KBAsGlobal_2023_March_01_POL")

    # commodity_areas = ee.Image().paint(kbas_2023_poly,1)

    # Cache keys for each risk level tile layer
    high_risk_tile_cache_key = 'high_risk_tile_layer'
    low_risk_tile_cache_key = 'low_risk_tile_layer'
    more_info_needed_tile_cache_key = 'more_info_needed_tile_layer'

    # Fetch data from the RESTful API endpoint.
    base_url = f"{request.scheme}://{request.get_host()}"
    response = requests.get(f"""{base_url}/api/farm/map/list/""") if not fileId and not farmId else requests.get(f"""{base_url}/api/farm/list/{farmId}""") if farmId else requests.get(
        f"""{base_url}/api/farm/list/file/{fileId}/""")
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

            # Create a FeatureCollection for high risk level farms
            high_risk_farms = ee.FeatureCollection([
                ee.Feature(ee.Geometry.Polygon(farm['polygon']), {
                    'color': "#F64468",  # Border color
                    # Background color with low opacity
                    'fillColor': '#f495a8'
                })
                for farm in farms if farm['analysis']['eudr_risk_level'] == 'high'
            ])

            # Low-risk farms with border and low-opacity background
            low_risk_farms = ee.FeatureCollection([
                ee.Feature(ee.Geometry.Polygon(farm['polygon']) if not farm['polygon'] or not len(farm['polygon']) == 2 else ee.Geometry.Point([farm['latitude'], farm['longitude']]), {
                    'color': "#3AD190",  # Border color
                    # Background color with low opacity
                    'fillColor': 'rgba(58, 209, 144, 0.3)'
                })
                for farm in farms if farm['analysis']['eudr_risk_level'] == 'low'
            ])

            # Farms needing more information with border and low-opacity background
            more_info_needed_farms = ee.FeatureCollection([
                ee.Feature(ee.Geometry.Polygon(farm['polygon']), {
                    'color': "#ACDCE8",  # Border color
                    # Background color with low opacity
                    'fillColor': 'rgba(172, 220, 232, 0.3)'
                })
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
                # cache.set(high_risk_tile_cache_key, high_risk_tile_layer,
                #           timeout=3600)  # Cache for 1 hour

            if not low_risk_tile_layer:
                low_risk_layer = ee.Image().paint(low_risk_farms, 1, 2)
                low_risk_tile_layer = geemap.ee_tile_layer(
                    low_risk_layer, {'palette': ["#3AD190"]}, 'EUDR Risk Level (Low)', shown=True)
                # cache.set(low_risk_tile_cache_key,
                #           low_risk_tile_layer, timeout=3600)

            if not more_info_needed_tile_layer:
                more_info_needed_layer = ee.Image().paint(more_info_needed_farms, 1, 2)
                more_info_needed_tile_layer = geemap.ee_tile_layer(more_info_needed_layer, {
                                                                   'palette': ["#ACDCE8"]}, 'EUDR Risk Level (More Info Needed)', shown=True)
                # cache.set(more_info_needed_tile_cache_key,
                #           more_info_needed_tile_layer, timeout=3600)

            # Add the high risk level farms to the map
            m.add_child(high_risk_tile_layer)

            # Add the low risk level farms to the map
            m.add_child(low_risk_tile_layer)

            # Add the more info needed farms to the map
            m.add_child(more_info_needed_tile_layer)

            for farm in farms:
                # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
                if 'polygon' in farm and len(farm['polygon']) == 1:
                    polygon = farm['polygon']

                    if polygon:
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
                        geo_pol = folium.GeoJson(data=js, control=False, style_function=lambda x: {
                            'color': 'transparent', 'fillColor': 'transparent'})
                        folium.Popup(
                            html=f"""
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
                                         'low' else 'red' if farm['analysis']['eudr_risk_level'] == 'high' else 'skyblue', icon='leaf'),
                    ).add_to(m)

            # zoom to the extent of the map to the first polygon
            has_polygon = next(
                (farm['polygon'] for farm in farms if farm['id'] == farmId and not farm['polygon'] or not len(farm['polygon']) == 2), farms[0]['polygon'] if not farm['polygon'] or not len(farm['polygon']) == 2 else None)
            if has_polygon:
                m.fit_bounds([reverse_polygon_points(has_polygon)],
                             max_zoom=14 if not farmId else 16)
            else:
                m.fit_bounds(
                    [[farms[0]['latitude'], farms[0]['longitude']]], max_zoom=18)
    else:
        print("Failed to fetch data from the API")

    deforestation_vis = {'palette': ['#900850']}
    deforestation_map = geemap.ee_tile_layer(
        deforestation, deforestation_vis, 'Deforestation (2021-2023)', shown=False)
    m.add_child(deforestation_map)

    # Add protected areas layer
    protected_areas_vis = {'palette': ['#585858']}
    protected_areas_map = geemap.ee_tile_layer(
        protected_areas, protected_areas_vis, 'Protected Areas', shown=False)
    m.add_child(protected_areas_map)

    # commodity_areas_vis = {'palette': ['#111111']}
    # commodity_areas_map = geemap.ee_tile_layer(
    #     commodity_areas, commodity_areas_vis, 'Commodity Areas', shown=False)
    # m.add_child(commodity_areas_map)

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
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #900850; width: 10px; height: 10px; border-radius: 30px;"></div>Deforestated Areas (2021-2023)</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #585858; width: 10px; height: 10px; border-radius: 30px;"></div>Protected Areas (2021-2023)</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Generate map HTML
    map_html = m._repr_html_()

    return JsonResponse({'map_html': map_html})


def reverse_polygon_points(polygon):
    reversed_polygon = [[lon, lat] for lat, lon in polygon[0]]
    return reversed_polygon
