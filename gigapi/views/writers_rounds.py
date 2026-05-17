from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import WritersRound
from .venues import VenueSerializer, Venue


class WritersRoundSerializer(serializers.ModelSerializer):
    venue = VenueSerializer()

    class Meta:
        model = WritersRound
        fields = ['id', 'user', 'event_title', 'date', 'start_time', 'end_time', 'venue']


class WritersRoundViewSet(viewsets.ViewSet):

    def list(self, request):
        writers_rounds = WritersRound.objects.select_related('venue').all()
        serializer = WritersRoundSerializer(writers_rounds, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        venue_id = request.data.get('venue_id') or request.data.get('venue')

        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

        writers_round = WritersRound.objects.create(
            venue=venue,
            event_title=request.data.get('event_title'),
            date=request.data.get('date'),
            start_time=request.data.get('start_time'),
            end_time=request.data.get('end_time'),
        )

        serializer = WritersRoundSerializer(writers_round, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            writers_round = WritersRound.objects.select_related('venue').get(pk=pk)
            serializer = WritersRoundSerializer(writers_round, context={'request': request})
            return Response(serializer.data)
        except WritersRound.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            writers_round = WritersRound.objects.get(pk=pk)

            venue_id = request.data.get('venue_id') or request.data.get('venue')
            try:
                venue = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

            writers_round.event_title = request.data.get('event_title', writers_round.event_title)
            writers_round.date = request.data.get('date', writers_round.date)
            writers_round.start_time = request.data.get('start_time', writers_round.start_time)
            writers_round.end_time = request.data.get('end_time', writers_round.end_time)
            writers_round.venue = venue
            writers_round.save()

            serializer = WritersRoundSerializer(writers_round, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except WritersRound.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            writers_round = WritersRound.objects.get(pk=pk)
            writers_round.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WritersRound.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
