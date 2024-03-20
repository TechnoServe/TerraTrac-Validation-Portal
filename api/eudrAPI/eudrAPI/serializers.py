from rest_framework import serializers


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class QueryAPISerializer(serializers.Serializer):
    alias = serializers.CharField()
    email = serializers.EmailField()
    organization = serializers.CharField()
    domains = serializers.ListField(child=serializers.CharField())
