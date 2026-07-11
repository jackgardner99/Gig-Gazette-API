from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import OpenMic
from .venues import Venue, VenueSerializer


class OpenMicSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    venue = VenueSerializer()

    def get_is_owner(self, obj):
        request = self.context['request']
        if not request.user.is_authenticated:
            return False
        return request.user == obj.user

    class Meta:
        model = OpenMic
        fields = ['id', 'user', 'event_title', 'recurrence', 'start_time', 'end_time', 'event_image', 'is_owner', 'venue', 'description', 'website_url']


class OpenMicViewSet(viewsets.ViewSet):

    def list(self, request):
        open_mics = OpenMic.objects.select_related('venue').all()
        serializer = OpenMicSerializer(open_mics, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            open_mic = OpenMic.objects.select_related('venue').get(pk=pk)
            serializer = OpenMicSerializer(open_mic, context={'request': request})
            return Response(serializer.data)
        except OpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        venue_id = request.data.get('venue')
        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

        open_mic = OpenMic.objects.create(
            user=request.user,
            event_title=request.data.get('event_title'),
            recurrence=request.data.get('recurrence'),
            start_time=request.data.get('start_time'),
            end_time=request.data.get('end_time'),
            event_image=request.data.get('event_image'),
            description=request.data.get('description'),
            website_url=request.data.get('website_url'),
            venue=venue
        )

        serializer = OpenMicSerializer(open_mic, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            open_mic = OpenMic.objects.get(pk=pk)

            venue_id = request.data.get('venue_id') or request.data.get('venue')
            try:
                venue = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

            open_mic.event_title = request.data.get('event_title', open_mic.event_title)
            open_mic.recurrence = request.data.get('recurrence', open_mic.recurrence)
            open_mic.start_time = request.data.get('start_time', open_mic.start_time)
            open_mic.end_time = request.data.get('end_time', open_mic.end_time)
            open_mic.event_image = request.data.get('event_image', open_mic.event_image)
            open_mic.description = request.data.get('description', open_mic.description)
            open_mic.website_url = request.data.get('website_url', open_mic.website_url)
            open_mic.venue = venue
            open_mic.save()

            serializer = OpenMicSerializer(open_mic, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except OpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            open_mic = OpenMic.objects.get(pk=pk)
            open_mic.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except OpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
