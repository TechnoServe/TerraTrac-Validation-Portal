from rest_framework import serializers
from .models import EUDRCollectionSiteModel, EUDRFarmBackupModel, EUDRFarmModel, EUDRUploadedFilesModel, EUDRUserModel


class EUDRUserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRUserModel
        fields = "__all__"


class EUDRFarmModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRFarmModel
        fields = "__all__"


class EUDRUploadedFilesModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRUploadedFilesModel
        fields = "__all__"


class EUDRFarmBackupModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRFarmBackupModel
        fields = "__all__"

class EUDRCollectionSiteModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EUDRCollectionSiteModel
        fields = "__all__"