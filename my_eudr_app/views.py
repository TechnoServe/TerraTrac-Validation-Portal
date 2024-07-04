from django.http import HttpResponse, JsonResponse
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
            return redirect('users')
    else:
        form = UserCreationForm()
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('users')
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


def map_view(request):
    initialize_earth_engine()

    # Create a Folium map object.
    m = folium.Map(location=[-1.964959990770339, 30.06470165146533],
                   zoom_start=5, control_scale=True, tiles=None)

    # Add base layers.
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}', attr='Google', name='Google Maps').add_to(m)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                     attr='Google', name='Google Satellite', show=False).add_to(m)

    # Fetch data from the RESTful API endpoint.
    response = requests.get('http://127.0.0.1:8000/api/farm/list/')
    if response.status_code == 200:
        farms = response.json()

        # Add deforestation layer (2021-2023)
        deforestation = ee.Image(
            'UMD/hansen/global_forest_change_2023_v1_11').select('lossyear').eq(1).selfMask()
        # Fetch protected areas
        protected_areas = ee.FeatureCollection("WCMC/WDPA/current/polygons")

        for farm in farms:
            # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
            if 'polygon' in farm:
                polygon = farm['polygon']
                if polygon:
                    farm_feature = ee.Feature(ee.Geometry.Polygon(polygon))
                    intersecting_areas = protected_areas.filterBounds(
                        farm_feature.geometry())
                    # Check if the farm intersects with deforestation areas
                    intersecting_deforestation = deforestation.reduceRegions(collection=ee.FeatureCollection(
                        [farm_feature]), reducer=ee.Reducer.anyNonZero(), scale=30).first().get('any').getInfo()

                    # Check if the farm intersects with any protected areas
                    if intersecting_areas.size().getInfo() > 0:
                        color = 'gray'
                    elif intersecting_deforestation:
                        color = 'red'
                    else:
                        color = 'green'

                    # if intersecting_deforestation or intersecting_areas.size().getInfo() > 0, update farm analysis
                    try:
                        if intersecting_deforestation or intersecting_areas.size().getInfo() > 0:
                            farm['analysis'] = {
                                'deforestation':
                                    True if intersecting_deforestation else False,
                                'protected_areas': intersecting_areas.size().getInfo() > 0 or False
                            }
                        else:
                            farm['analysis'] = {
                                'deforestation': False,
                                'protected_areas': False
                            }
                        # Update farm analysis in the API
                        requests.put(
                            f'http://localhost:8000/api/farm/update/{farm["id"]}/', json=farm)
                    except Exception as e:
                        print(f"Failed to update farm analysis: {e}")

                    folium.GeoJson(
                        {
                            "type": "Feature",
                            "properties": {
                                "farmer_name": farm['farmer_name'],
                                "farm_size": farm.get('farm_size', 'N/A')
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [polygon]
                            }
                        },
                        control=False,
                        popup=f"<b>Farmer Name:</b> {
                            farm['farmer_name']}<br/>",
                        style_function=lambda x, color=color: {
                            'color': color, 'fillColor': color}
                    ).add_to(m)
            else:
                folium.Marker(
                    location=[farm['latitude'], farm['longitude']],
                    popup=farm['farmer_name'],
                    icon=folium.Icon(color='green', icon='leaf')
                ).add_to(m)
    else:
        print("Failed to fetch data from the API")

    deforestation_vis = {'palette': ['FF0000']}
    deforestation_map = geemap.ee_tile_layer(
        deforestation, deforestation_vis, 'Deforestation (2021-2023)', shown=False)
    m.add_child(deforestation_map)

    # Add protected areas layer
    protected_areas_map = geemap.ee_tile_layer(
        protected_areas, {}, 'Protected Areas', shown=False)
    m.add_child(protected_areas_map)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed;
                bottom: 160px; right: 10px; width: 250px; height: auto;
                margin-bottom: 10px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding: 10px;">
    <h4>Legend</h4><br/>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #A9E0B5; border: 1px solid green; width: 10px; height: 10px; border-radius: 30px;"></div>Valid Farms</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #DCC6B5; border: 1px solid red; width: 10px; height: 10px; border-radius: 30px;"></div> Farms in Deforestated Areas (2021-2023)</div>
    <div style="display: flex; gap: 10px; align-items: center;"><div style="background: #A2B1A8; border: 1px solid gray; width: 10px; height: 10px; border-radius: 30px;"></div> Farms in Protected Areas (2021-2023)</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Generate map HTML
    map_html = m._repr_html_()

    return render(request, 'map.html', {'map_html': map_html})
