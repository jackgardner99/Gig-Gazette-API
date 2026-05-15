from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import Show
from .clients import Client, ClientSerializer
from .venues import Venue, VenueSerializer

class ShowSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    client = ClientSerializer()
    venue = VenueSerializer()

    def get_is_owner(self, obj):
        request = self.context['request']
        if not request.user.is_authenticated:
            return False
        return request.user == obj.client.user
    
    class Meta:
        model = Show
        fields = ['id', 'client', 'is_owner', 'event_title', 'poster_img', 'date', 'start_time', 'end_time', 'venue']

class ShowWriteSerializer(serializers.ModelSerializer):
    client = serializers.ListField(child=serializers.PrimaryKeyRelatedField(queryset=Client.objects.all()), required=False)

    class Meta:
        model = Show
        fields = ['client', 'event_title', 'poster_img', 'date', 'start_time', 'end_time', 'venue']


class ShowViewSet(viewsets.ViewSet):

    def list(self, request):
        shows = Show.objects.all()
        serializer = ShowSerializer(shows, many=True, context={'request': request})
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        try:
            show= Show.objects.get(pk=pk)
            serializer = ShowSerializer(show, context={'request': request})
            return Response(serializer.data)
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        venue_id = request.data.get('venue_id') or request.data.get('venue')

        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

        show = Show.objects.create(
            venue=venue,
            event_title=request.data.get('event_title'),
            poster_img=request.data.get('poster_img'),
            date=request.data.get('date'),
            start_time=request.data.get('start_time'),
            end_time=request.data.get('end_time'),
        )

        serializer = ShowSerializer(show, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:

            show = Show.objects.get(pk=pk)

            self.check_object_permissions(request, show)

            serializer = ShowWriteSerializer(data=request.data)
            if serializer.is_valid():
                client_id = request.data.get('client_id')
                try:
                    client = Client.objects.get(pk=client_id)
                except Client.DoesNotExist:
                    return Response({'error': 'Genre not found'}, status=status.HTTP_400_BAD_REQUEST)

                show.event_title = serializer.validated_data['event_title']
                show.poster_img = serializer.validated_data['poster_img']
                show.client = client
                show.date = serializer.validated_data['date']
                show.start_time = serializer.validated_data['start_time']
                show.end_time = serializer.validated_data['end_time']
                show.save()

                serializer = ShowSerializer(show, context={'request': request})
                return Response(status=status.HTTP_204_NO_CONTENT)
            
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            show = Show.objects.get(pk=pk)
            if show.client.user.id == request.auth.user.id:

                self.check_object_permissions(request, show)
                show.delete()

                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'message': "You do not own this show"}, status=status.HTTP_403_FORBIDDEN)
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)