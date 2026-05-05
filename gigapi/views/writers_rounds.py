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

    def retrieve(self, request, pk=None):
        try:
            writers_round = WritersRound.objects.select_related('venue').get(pk=pk)
            serializer = WritersRoundSerializer(writers_round, context={'request': request})
            return Response(serializer.data)
        except WritersRound.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
