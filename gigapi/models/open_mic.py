from django.db import models
from django.contrib.auth.models import User


class OpenMic(models.Model):
    event_title = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="open_mics")
    recurrence = models.BooleanField(default=False)
    weekly_recurrence = models.CharField(max_length=255, blank=True, null=True)
    monthly_recurrence = models.CharField(max_length=255, blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    event_image = models.ImageField(upload_to="open_mics/", blank=True, null=True)

    class Meta:
        db_table = "open_mics"
