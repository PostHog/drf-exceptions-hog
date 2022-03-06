from django.db import models


# A group of hedgehogs is called an array
class ArrayModel(models.Model):
    name: models.CharField = models.CharField(max_length=128)


class Hedgehog(models.Model):
    name: models.CharField = models.CharField(max_length=128)
    color: models.CharField = models.CharField(max_length=32, default="blue")
    age: models.IntegerField = models.IntegerField(default=0)
    array: models.ForeignKey = models.ForeignKey(
        ArrayModel,
        related_name="array",
        related_query_name="hedgehogs",
        on_delete=models.CASCADE,
        null=True,
    )
