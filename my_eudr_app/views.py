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
    image2023 = ee.Image(
        'UMD/hansen/global_forest_change_2023_v1_11').select('lossyear').eq(1).selfMask()

    # Add deforestation layer (2021-2023)
    deforestation = image2023
    # Fetch protected areas
    protected_areas = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    # Fetch data from the RESTful API endpoint.
    response = requests.get('http://127.0.0.1:8000/api/farm/map/list/') if not fileId else requests.get(
        f'http://127.0.0.1:8000/api/farm/list/file/{fileId}/')
    if response.status_code == 200:
        farms = response.json()
        color = 'green'
        if len(farms) > 0:
            for farm in farms:
                # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
                if 'polygon' in farm:
                    polygon = farm['polygon']
                    if polygon:
                        if farm['analysis']['is_in_protected_areas'] != '-':
                            color = 'gray'
                        elif farm['analysis']['tree_cover_loss'] == 'yes':
                            color = 'red'
                        else:
                            color = 'green'
                        folium.Polygon(
                            locations=[reverse_polygon_points(polygon)],
                            tooltip=f"""<b>Farmer Name:</b> {farm['farmer_name']}<br>
            <b>Farm Size:</b> {farm['farm_size']}<br>
            <b>Collection Site:</b> {farm['collection_site']}<br>
            <b>Agent Name:</b> {farm['agent_name']}<br>
            <b>Farm Village:</b> {farm['farm_village']}<br>
            <b>District:</b> {farm['farm_district']}<br>
            <b>Is in Deforested Area:</b> {farm['analysis']['tree_cover_loss']}<br/>
            <b>Is in Protected Area:</b> {'Yes' if farm['analysis']['is_in_protected_areas'] != '-' else 'No'}<br/>
            """,
                            color=color,
                            fill=True,
                            fill_color=color
                        ).add_to(m)
                else:
                    folium.Marker(
                        location=[farm['latitude'], farm['longitude']],
                        popup=folium.Popup(html=f"""<b>Farmer Name:</b> {farm['farmer_name']}<br>
            <b>Farm Size:</b> {farm['farm_size']}<br>
            <b>Collection Site:</b> {farm['collection_site']}<br>
            <b>Agent Name:</b> {farm['agent_name']}<br>
            <b>Farm Village:</b> {farm['farm_village']}<br>
            <b>District:</b> {farm['farm_district']}<br>
            <b>Is in Deforested Area:</b> {farm['analysis']['tree_cover_loss']}<br/>
            <b>Is in Protected Area:</b> {'Yes' if farm['analysis']['is_in_protected_areas'] != '-' else 'No'}<br/>
            """, show=True),
                        icon=folium.Icon(color='green', icon='leaf'),
                    ).add_to(m)

            # zoom to the extent of the map to the first polygon
            has_polygon = next(
                (farm['polygon'] for farm in farms if farm['id'] == farmId), farms[0]['polygon'])
            if has_polygon:
                m.fit_bounds([reverse_polygon_points(has_polygon)],
                             max_zoom=14 if not farmId else 16)
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


def reverse_polygon_points(polygon):
    reversed_polygon = [[lon, lat] for lat, lon in polygon[0]]
    return reversed_polygon
