from django.db import models
from .genre import Genre
from .artist import Artist


class Client(models.Model):
    client_name = models.CharField(max_length=255)
    is_band = models.BooleanField(default=False)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    artists = models.ManyToManyField(Artist, related_name="artists")

    class Meta:
        db_table = "clients"
