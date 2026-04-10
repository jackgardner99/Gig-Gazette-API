from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.response import Response
from gigapi.models import Venue

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'lat', 'lng', 'noise_level', 'parking', 'bar', 'food', 'kid_friendly']

class VenueViewSet(viewsets.ViewSet):

    def list(self, request):
        venues = Venue.objects.all()
        serializer = VenueSerializer(venues, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        try:
            venue = Venue.objects.get(pk=pk)
            serializer = VenueSerializer(venue)
            return Response(serializer.data)
        except Venue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)