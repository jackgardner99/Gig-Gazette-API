from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from gigapi.views import ClientViewSet, GenreViewSet, ArtistViewSet, VenueViewSet, OpenMicViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'clients', ClientViewSet, 'client')
router.register(r'genres', GenreViewSet, 'genre')
router.register(r'artists', ArtistViewSet, 'artist')
router.register(r'venues', VenueViewSet, 'venue')
router.register(r'open_mics', OpenMicViewSet, 'open_mic')

urlpatterns = [
    path('', include(router.urls)),
]

