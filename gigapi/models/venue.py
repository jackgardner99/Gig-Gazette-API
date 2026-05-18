from django.db import models
from django.contrib.auth.models import User


class Venue(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="venues", null=True, blank=True)
    name = models.CharField(max_length=255)
    address_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    noise_level = models.CharField(max_length=255, blank=True, null=True)
    parking = models.BooleanField(default=False)
    bar = models.BooleanField(default=False)
    food = models.BooleanField(default=False)
    kid_friendly = models.BooleanField(default=False)
    venue_image = models.ImageField(upload_to="venues/", blank=True, null=True)

    class Meta:
        db_table = "venues"
