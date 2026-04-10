from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "genres"
