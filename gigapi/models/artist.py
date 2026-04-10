from django.db import models


class Artist(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "artists"
