from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.response import Response
from gigapi.models import Artist

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name']

class ArtistViewSet(viewsets.ViewSet):

    def list(self, request):
        artists = Artist.objects.all()
        serializer = ArtistSerializer(artists, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        try:
            artist = Artist.objects.get(pk=pk)
            serializer = ArtistSerializer(artist)
            return Response(serializer.data)
        except Artist.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)