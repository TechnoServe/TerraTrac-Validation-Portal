from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
import ee
import folium
import geemap.foliumap as geemap
import requests
from shapely import Polygon
from eudr_backend.settings import initialize_earth_engine
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_decode
from eudr_backend.views import flatten_geojson, flatten_multipolygon_coordinates, is_valid_polygon
from my_eudr_app.ee_images import combine_commodities_images, combine_disturbances_after_2020_images, combine_disturbances_before_2020_images, combine_forest_cover_images
from django.utils import timezone
from eudr_backend.models import EUDRSharedMapAccessCodeModel


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('username')
            user.save()
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
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Important to keep the user logged in
            update_session_auth_hash(request, user)
            messages.success(
                request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


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


def shared_map(request):
    active_page = "shared_map"

    return render(request, "shared_map.html", {"active_page": active_page, 'user': request.user})


@login_required
@staff_member_required(login_url='/login/')
def users(request):
    active_page = "users"

    return render(request, "users.html", {"active_page": active_page, 'user': request.user})


@login_required
@staff_member_required(login_url='/login/')
def all_uploaded_files(request):
    active_page = "uploads"

    return render(request, "uploads.html", {"active_page": active_page, 'user': request.user})


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'profile.html')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')


def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(email=data)
            if associated_users.exists():
                for user in associated_users:
                    subject = "TerraTrav Validation Portal - Password Reset Requested"
                    email_template_name = "auth/password_reset_email.html"
                    c = {
                        "email": user.email,
                        "domain": request.get_host(),
                        "site_name": "TerraTrac Validation Portal",
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        "token": default_token_generator.make_token(user),
                        "protocol": 'https' if request.is_secure() else 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    send_mail(subject, message=email, html_message=email,
                              from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email])

                messages.success(
                    request, 'A link to reset your password has been sent to your email address.')
                return redirect(reverse('password_reset'))
            else:
                messages.error(
                    request, 'No user found with this email address.')
                return redirect(reverse('password_reset'))

    password_reset_form = PasswordResetForm()
    return render(request, "auth/password_reset.html", {"form": password_reset_form})


def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(
                    request, 'Your password has been successfully reset. You can now log in with your new password.')
                return redirect('login')
        else:
            form = SetPasswordForm(user)
    else:
        messages.error(
            request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset')

    return render(request, 'auth/password_reset_confirm.html', {'form': form})


def map_view(request):
    fileId = request.GET.get('file-id')
    accessCode = request.GET.get('access-code')
    farmId = request.GET.get('farm-id')
    overLap = 'overlaps' in request.META.get('HTTP_REFERER').split('/')[-1]
    userLat = request.GET.get('lat') or 0.0
    userLon = request.GET.get('lon') or 0.0
    farmId = int(farmId) if farmId else None

    if accessCode:
        try:
            access_record = EUDRSharedMapAccessCodeModel.objects.get(
                file_id=fileId, access_code=accessCode)
            if access_record.valid_until and access_record.valid_until < timezone.now():
                return JsonResponse({"message": "Access Code Expired", "status": 403})
        except BaseException:
            return JsonResponse(
                {"message": "Invalid file ID or access code.", "status": 403})

    initialize_earth_engine()

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
        f"""{base_url}/api/farm/list/file/{fileId}/""") if not overLap else requests.get(f"""{base_url}/api/farm/overlapping/{fileId}/""")
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
                    polygon = flatten_multipolygon_coordinates(farm['polygon'])

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

    return JsonResponse({'map_html': map_html})


def reverse_polygon_points(polygon):
    reversed_polygon = [[lon, lat] for lat, lon in polygon[0]]
    return reversed_polygon
