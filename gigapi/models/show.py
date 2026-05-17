from django.db import models
from django.contrib.auth.models import User
from .venue import Venue


class Show(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="shows", null=True, blank=True)
    event_title = models.CharField(max_length=255)
    poster_img = models.ImageField(upload_to="posters/", blank=True, null=True)
    ticket_link = models.URLField(blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="shows")

    class Meta:
        db_table = "shows"
