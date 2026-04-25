from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import Client
from .artists import ArtistSerializer, Artist
from .genres import GenreSerializer, Genre

class ClientSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    artists = ArtistSerializer(many=True)
    genre = GenreSerializer()

    def get_is_owner(self, obj):
        request = self.context['request']
        if not request.user.is_authenticated:
            return False
        return request.user == obj.user
    
    class Meta:
        model = Client
        fields = ['id', 'user', 'client_name', 'is_band', 'genre', 'is_owner', 'artists', 'client_image']

class ClientWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['client_name', 'is_band']


class ClientViewSet(viewsets.ViewSet):

    def list(self, request):
        clients = Client.objects.all()
        serializer = ClientSerializer(clients, many=True, context={'request': request})
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        try:
            client= Client.objects.get(pk=pk)
            serializer = ClientSerializer(client, context={'request': request})
            return Response(serializer.data)
        except Client.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def create(self, request):
        # Get the data from the client's JSON payload
        client_name = request.data.get('client_name')
        is_band = request.data.get('is_band')
        genre_id = request.data.get('genre_id')
        client_image = request.data.get('client_image')

        try:
            genre = Genre.objects.get(pk=genre_id)
        except Genre.DoesNotExist:
            return Response({'error': 'Genre not found'}, status=status.HTTP_400_BAD_REQUEST)

        client = Client.objects.create(
            user=request.user,
            client_name=client_name,
            is_band=is_band,
            genre=genre,
            client_image=client_image
        )

        # Establish the many-to-many relationships
        artist_ids = request.data.get('artists', [])
        client.artists.set(artist_ids)

        serializer = ClientSerializer(client, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        try:

            client = Client.objects.get(pk=pk)

            self.check_object_permissions(request, client)

            serializer = ClientWriteSerializer(data=request.data)
            if serializer.is_valid():
                genre_id = request.data.get('genre_id') or request.data.get('genre')
                try:
                    genre = Genre.objects.get(pk=genre_id)
                except Genre.DoesNotExist:
                    return Response({'error': 'Genre not found'}, status=status.HTTP_400_BAD_REQUEST)

                client.client_name = serializer.validated_data['client_name']
                client.is_band = serializer.validated_data['is_band']
                client.client_image = serializer.validated_data['client_image']
                client.genre = genre
                client.save()

                artist_ids = request.data.get('artists', [])
                client.artists.set(artist_ids)

                serializer = ClientSerializer(client, context={'request': request})
                return Response(status=status.HTTP_204_NO_CONTENT)
            
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        
        except Client.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def destroy(self, request, pk=None):
        try:
            client = Client.objects.get(pk=pk)
            self.check_object_permissions(request, client)
            client.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Client.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)