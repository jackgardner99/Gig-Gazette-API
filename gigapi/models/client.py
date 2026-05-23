from django.db import models
from django.contrib.auth.models import User
from .genre import Genre
from .artist import Artist


class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books_created")
    client_name = models.CharField(max_length=255)
    is_band = models.BooleanField(default=False)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    artists = models.ManyToManyField(Artist, related_name="artists")
    client_image = models.ImageField(upload_to="clients/", blank=True, null=True)

    class Meta:
        db_table = "clients"
