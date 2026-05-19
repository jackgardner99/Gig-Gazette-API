from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.response import Response
from gigapi.models import Venue, Restaurant
import re
import requests


def geocode_location(address_number, address, city, state, country="US"):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "street": f"{address_number} {address}",
            "city": city,
            "state": state,
            "country": country,
            "format": "json",
            "limit": 1,
        },
        headers={"User-Agent": "GigGazette/1.0"}
    )
    results = response.json()
    if results:
        return float(results[0]["lat"]), float(results[0]["lon"])

    fallback = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": f"{address_number} {address}, {city}, {state}, {country}",
            "format": "json",
            "limit": 1,
        },
        headers={"User-Agent": "GigGazette/1.0"}
    )
    fallback_results = fallback.json()
    if fallback_results:
        return float(fallback_results[0]["lat"]), float(fallback_results[0]["lon"])

    numeric_number = re.sub(r'[^0-9]', '', address_number)
    if numeric_number != address_number:
        stripped = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{numeric_number} {address}, {city}, {state}, {country}",
                "format": "json",
                "limit": 1,
            },
            headers={"User-Agent": "GigGazette/1.0"}
        )
        stripped_results = stripped.json()
        if stripped_results:
            return float(stripped_results[0]["lat"]), float(stripped_results[0]["lon"])

    return None, None

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'food_type', 'lat', 'lng', 'is_visible']

class VenueSerializer(serializers.ModelSerializer):
    restaurants = RestaurantSerializer(many=True)

    class Meta:
        model = Venue
        fields = ['id', 'user', 'name', 'address_number', 'address', 'city', 'state', 'country', 'lat', 'lng', 'noise_level', 'parking', 'bar', 'food', 'kid_friendly', 'restaurants', 'venue_image']

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
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        address_number = request.data.get('address_number')
        address = request.data.get('address')
        city = request.data.get('city')
        state = request.data.get('state')
        country = request.data.get('country', 'US')

        if not address_number or not address or not city or not state:
            return Response({'error': 'address_number, address, city, and state are required'}, status=status.HTTP_400_BAD_REQUEST)

        lat, lng = geocode_location(address_number, address, city, state, country)
        if lat is None or lng is None:
            return Response({'error': 'Could not resolve address to coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        venue = Venue.objects.create(
            user=request.user,
            name=request.data.get('name'),
            address_number=address_number,
            address=address,
            city=city,
            state=state,
            country=country,
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

            address_number = request.data.get('address_number', venue.address_number)
            address = request.data.get('address', venue.address)
            city = request.data.get('city', venue.city)
            state = request.data.get('state', venue.state)
            country = request.data.get('country', venue.country)

            if any([request.data.get('address_number'), request.data.get('address'), request.data.get('city'), request.data.get('state')]):
                lat, lng = geocode_location(address_number, address, city, state, country)
                if lat is None or lng is None:
                    return Response({'error': 'Could not resolve address to coordinates'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                lat, lng = venue.lat, venue.lng

            venue.name = request.data.get('name', venue.name)
            venue.address_number = address_number
            venue.address = address
            venue.city = city
            venue.state = state
            venue.country = country
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

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            venue = Venue.objects.get(pk=pk)

            if venue.user != request.user:
                return Response({'error': 'You do not own this venue'}, status=status.HTTP_403_FORBIDDEN)

            venue.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Venue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)