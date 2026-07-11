from django.db import models
from django.contrib.auth.models import User
from .venue import Venue


class OpenMic(models.Model):
    event_title = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="open_mics", null=True, blank=True)
    recurrence = models.CharField(max_length=255, blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    event_image = models.ImageField(upload_to="open_mics/", blank=True, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="open_mics")
    description = models.CharField(max_length=5000, blank=True, default='')
    website_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "open_mics"
