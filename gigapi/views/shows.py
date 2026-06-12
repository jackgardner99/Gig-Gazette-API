from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import Show
from .venues import Venue, VenueSerializer


class ShowSerializer(serializers.ModelSerializer):
    venue = VenueSerializer()

    class Meta:
        model = Show
        fields = ['id', 'user', 'event_title', 'poster_img', 'ticket_link', 'recurrence', 'date', 'start_time', 'end_time', 'venue', 'description']


class ShowViewSet(viewsets.ViewSet):

    def list(self, request):
        shows = Show.objects.select_related('venue').all()
        user_id = request.query_params.get('userId')
        if user_id:
            shows = shows.filter(user__id=user_id)
        serializer = ShowSerializer(shows, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            show = Show.objects.select_related('venue').get(pk=pk)
            serializer = ShowSerializer(show, context={'request': request})
            return Response(serializer.data)
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        recurrence = request.data.get('recurrence') or None
        date = request.data.get('date') or None

        if not recurrence and not date:
            return Response({'error': 'Either date or recurrence is required'}, status=status.HTTP_400_BAD_REQUEST)

        venue_id = request.data.get('venue_id') or request.data.get('venue')

        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

        show = Show.objects.create(
            user=request.user,
            venue=venue,
            event_title=request.data.get('event_title'),
            poster_img=request.data.get('poster_img'),
            ticket_link=request.data.get('ticket_link'),
            recurrence=recurrence,
            date=date,
            start_time=request.data.get('start_time'),
            end_time=request.data.get('end_time'),
            description=request.data.get('description'),
        )

        serializer = ShowSerializer(show, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            show = Show.objects.get(pk=pk)

            venue_id = request.data.get('venue_id') or request.data.get('venue')
            try:
                venue = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

            show.event_title = request.data.get('event_title', show.event_title)
            show.poster_img = request.data.get('poster_img', show.poster_img)
            show.ticket_link = request.data.get('ticket_link', show.ticket_link)
            show.recurrence = request.data.get('recurrence', show.recurrence)
            show.date = request.data.get('date', show.date)
            show.start_time = request.data.get('start_time', show.start_time)
            show.end_time = request.data.get('end_time', show.end_time)
            show.description = request.data.get('description', show.description)
            show.venue = venue
            show.save()

            serializer = ShowSerializer(show, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            show = Show.objects.get(pk=pk)
            show.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
