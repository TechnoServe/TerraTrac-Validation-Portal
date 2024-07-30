from django.contrib import admin

from eudr_backend.models import WhispAPISetting, EUDRFarmModel

admin.site.register(
    [
        EUDRFarmModel,
        WhispAPISetting
    ]
)
