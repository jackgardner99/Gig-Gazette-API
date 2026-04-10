from django.db import models
from .venue import Venue


class Restaurant(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=255)
    food_type = models.CharField(max_length=255, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "restaurants"
