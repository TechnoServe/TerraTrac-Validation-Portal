from rest_framework import serializers
from .models import EUDRFarmModel


class EUDRFarmModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRFarmModel
        fields = "__all__"
