import os

import requests
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response

from gigapi.models import Restaurant, Venue


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return default


def geocode_location(address_number, address, city, state, country="US"):
    access_token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    search_text = f"{address_number} {address}, {city}, {state}, {country}"
    try:
        response = requests.get(
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(search_text)}.json",
            params={"access_token": access_token, "limit": 1, "types": "address"},
            timeout=10,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        if features:
            lon, lat = features[0]["geometry"]["coordinates"]
            return float(lat), float(lon), None
    except requests.RequestException as e:
        return None, None, str(e)
    return None, None, "no results"

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'food_type', 'lat', 'lng', 'is_visible']

class VenueSerializer(serializers.ModelSerializer):
    restaurants = RestaurantSerializer(many=True)

    class Meta:
        model = Venue
        fields = ['id', 'user', 'name', 'address_number', 'address', 'city', 'state', 'country', 'lat', 'lng', 'noise_level', 'parking', 'bar', 'food', 'kid_friendly', 'seating', 'requires_reservation', 'outdoor', 'beer_only', 'cover_charge', 'restaurants', 'venue_image', 'ical_feed_url', 'website_url']

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

        lat, lng, geo_error = geocode_location(address_number, address, city, state, country)
        if lat is None or lng is None:
            return Response({'error': 'Could not resolve address to coordinates', 'detail': geo_error}, status=status.HTTP_400_BAD_REQUEST)

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
            parking=parse_bool(request.data.get('parking', False)),
            bar=parse_bool(request.data.get('bar', False)),
            food=parse_bool(request.data.get('food', False)),
            kid_friendly=parse_bool(request.data.get('kid_friendly', False)),
            seating=parse_bool(request.data.get('seating', False)),
            requires_reservation=parse_bool(request.data.get('requires_reservation', False)),
            outdoor=parse_bool(request.data.get('outdoor', False)),
            beer_only=parse_bool(request.data.get('beer_only', False)),
            cover_charge=parse_bool(request.data.get('cover_charge', False)),
            venue_image=request.data.get('venue_image'),
            ical_feed_url=request.data.get('ical_feed_url'),
            website_url=request.data.get('website_url'),
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

            address_changed = (
                address_number != venue.address_number or
                address != venue.address or
                city != venue.city or
                state != venue.state or
                country != venue.country
            )

            if address_changed:
                lat, lng, geo_error = geocode_location(address_number, address, city, state, country)
                if lat is None or lng is None:
                    return Response({'error': 'Could not resolve address to coordinates', 'detail': geo_error}, status=status.HTTP_400_BAD_REQUEST)
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
            venue.parking = parse_bool(request.data.get('parking', venue.parking))
            venue.bar = parse_bool(request.data.get('bar', venue.bar))
            venue.food = parse_bool(request.data.get('food', venue.food))
            venue.kid_friendly = parse_bool(request.data.get('kid_friendly', venue.kid_friendly))
            venue.seating = parse_bool(request.data.get('seating', venue.seating))
            venue.requires_reservation = parse_bool(request.data.get('requires_reservation', venue.requires_reservation))
            venue.outdoor = parse_bool(request.data.get('outdoor', venue.outdoor))
            venue.beer_only = parse_bool(request.data.get('beer_only', venue.beer_only))
            venue.cover_charge = parse_bool(request.data.get('cover_charge', venue.cover_charge))
            venue.venue_image = request.data.get('venue_image', venue.venue_image)
            venue.ical_feed_url = request.data.get('ical_feed_url', venue.ical_feed_url)
            venue.website_url = request.data.get('website_url', venue.website_url)
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
