from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from gigapi.views import ClientViewSet, GenreViewSet, ArtistViewSet, VenueViewSet, OpenMicViewSet, ShowViewSet, Users, WritersRoundViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'clients', ClientViewSet, 'client')
router.register(r'genres', GenreViewSet, 'genre')
router.register(r'artists', ArtistViewSet, 'artist')
router.register(r'venues', VenueViewSet, 'venue')
router.register(r'open_mics', OpenMicViewSet, 'open_mic')
router.register(r'shows', ShowViewSet, 'show')
router.register(r'users', Users, 'user')
router.register(r'writers_rounds', WritersRoundViewSet, 'writers_round')

urlpatterns = [
    path('', include(router.urls)),
    path('login', csrf_exempt(Users.as_view({'post': 'login_user'}))),
    path('register', csrf_exempt(Users.as_view({'post': 'register'})))
]

