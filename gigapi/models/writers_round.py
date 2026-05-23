from django.db import models
from django.contrib.auth.models import User
from .venue import Venue

class WritersRound(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="writers_rounds", null=True, blank=True)
    event_title = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="writers_rounds")

    class Meta:
        db_table = "writers_rounds"

