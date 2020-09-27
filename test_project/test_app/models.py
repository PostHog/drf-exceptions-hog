from django.db import models


class Hedgehog(models.Model):
    name: models.CharField = models.CharField(max_length=128)
    color: models.CharField = models.CharField(max_length=32, default="blue")
    age: models.IntegerField = models.IntegerField(default=0)
