from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.response import Response
from gigapi.models import Venue, Restaurant
import requests


def geocode_location(location_string):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location_string, "format": "json", "limit": 1},
        headers={"User-Agent": "GigGazette/1.0"}
    )
    results = response.json()
    if results:
        return float(results[0]["lat"]), float(results[0]["lon"])
    return None, None

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'food_type', 'lat', 'lng', 'is_visible']

class VenueSerializer(serializers.ModelSerializer):
    restaurants = RestaurantSerializer(many=True)

    class Meta:
        model = Venue
        fields = ['id', 'name', 'lat', 'lng', 'noise_level', 'parking', 'bar', 'food', 'kid_friendly', 'restaurants', 'venue_image']

class VenueViewSet(viewsets.ViewSet):

    def list(self, request):
        venues = Venue.objects.prefetch_related('restaurants').all()
        serializer = VenueSerializer(venues, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            venue = Venue.objects.prefetch_related('restaurants').get(pk=pk)
            serializer = VenueSerializer(venue)
            return Response(serializer.data)
        except Venue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        location = request.data.get('location')
        lat, lng = geocode_location(location) if location else (
            request.data.get('lat'), request.data.get('lng')
        )

        if lat is None or lng is None:
            return Response({'error': 'Could not resolve location to coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        venue = Venue.objects.create(
            name=request.data.get('name'),
            lat=lat,
            lng=lng,
            noise_level=request.data.get('noise_level'),
            parking=request.data.get('parking', False),
            bar=request.data.get('bar', False),
            food=request.data.get('food', False),
            kid_friendly=request.data.get('kid_friendly', False),
            venue_image=request.data.get('venue_image'),
        )

        serializer = VenueSerializer(venue)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        try:
            venue = Venue.objects.get(pk=pk)

            location = request.data.get('location')
            lat, lng = geocode_location(location) if location else (
                request.data.get('lat', venue.lat),
                request.data.get('lng', venue.lng)
            )

            if lat is None or lng is None:
                return Response({'error': 'Could not resolve location to coordinates'}, status=status.HTTP_400_BAD_REQUEST)

            venue.name = request.data.get('name', venue.name)
            venue.lat = lat
            venue.lng = lng
            venue.noise_level = request.data.get('noise_level', venue.noise_level)
            venue.parking = request.data.get('parking', venue.parking)
            venue.bar = request.data.get('bar', venue.bar)
            venue.food = request.data.get('food', venue.food)
            venue.kid_friendly = request.data.get('kid_friendly', venue.kid_friendly)
            venue.venue_image = request.data.get('venue_image', venue.venue_image)
            venue.save()

            serializer = VenueSerializer(venue)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Venue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)