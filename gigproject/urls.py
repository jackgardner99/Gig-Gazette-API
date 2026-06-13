from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

from gigapi.views import ArtistViewSet, ClientViewSet, GenreViewSet, OpenMicViewSet, ShowViewSet, Users, VenueViewSet, WritersRoundViewSet, UserPhotoForOpenMicViewSet, UserPhotoForWritersRoundViewSet, UserPhotoForShowViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'clients', ClientViewSet, 'client')
router.register(r'genres', GenreViewSet, 'genre')
router.register(r'artists', ArtistViewSet, 'artist')
router.register(r'venues', VenueViewSet, 'venue')
router.register(r'open_mics', OpenMicViewSet, 'open_mic')
router.register(r'shows', ShowViewSet, 'show')
router.register(r'users', Users, 'user')
router.register(r'writers_rounds', WritersRoundViewSet, 'writers_round')
router.register(r'open_mic_photos', UserPhotoForOpenMicViewSet, 'open_mic_photo')
router.register(r'writers_round_photos', UserPhotoForWritersRoundViewSet, 'writers_round_photo')
router.register(r'show_photos', UserPhotoForShowViewSet, 'show_photo')

urlpatterns = [
    path('', include(router.urls)),
    path('login', csrf_exempt(Users.as_view({'post': 'login_user'}))),
    path('register', csrf_exempt(Users.as_view({'post': 'register'}))),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
