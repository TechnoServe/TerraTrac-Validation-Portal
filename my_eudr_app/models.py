from django.db import models


class BearerToken(models.Model):
    token = models.CharField(max_length=255)


class APIKey(models.Model):
    api_key = models.CharField(max_length=255)
    alias = models.CharField(max_length=100)
    email = models.EmailField()
    organization = models.CharField(max_length=100)
    domains = models.CharField(max_length=255)
