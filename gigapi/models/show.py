from django.db import models
from .client import Client


class Show(models.Model):
    event_title = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="shows")
    poster_img = models.ImageField(upload_to="posters/", blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = "shows"
