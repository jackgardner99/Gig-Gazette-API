from django.db import models
from django.contrib.auth.models import User
from .open_mic import OpenMic
from .show import Show
from .writers_round import WritersRound


class UserPhotoForOpenMic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="open_mic_photos")
    open_mic = models.ForeignKey(OpenMic, on_delete=models.CASCADE, related_name="user_photos")
    user_image = models.ImageField(upload_to="open_mic_photos/")

    class Meta:
        db_table = "user_photos_for_open_mic"


class UserPhotoForWritersRound(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="writers_round_photos")
    writers_round = models.ForeignKey(WritersRound, on_delete=models.CASCADE, related_name="user_photos")
    user_image = models.ImageField(upload_to="writers_round_photos/")

    class Meta:
        db_table = "user_photos_for_writers_round"


class UserPhotoForShow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="show_photos")
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="user_photos")
    user_image = models.ImageField(upload_to="show_photos/")

    class Meta:
        db_table = "user_photos_for_show"
