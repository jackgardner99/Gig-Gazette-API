from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from gigapi.views import ClientViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'clients', ClientViewSet, 'client')

urlpatterns = [
    path('', include(router.urls)),
]

