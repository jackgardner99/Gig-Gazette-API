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
        fields = ['id', 'user', 'event_title', 'recurrence', 'weekly_recurrence', 'monthly_recurrence', 'start_time', 'end_time', 'event_image', 'is_owner', 'venue']

class OpenMicWriteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = OpenMic
        fields = ['user', 'event_title', 'recurrence', 'weekly_recurrence', 'monthly_recurrence', 'start_time', 'end_time', 'event_image', 'venue']


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
        event_title = request.data.get('event_title')
        recurrence = request.data.get('recurrence')
        weekly_recurrence = request.data.get('weekly_recurrence')
        monthly_recurrence = request.data.get('monthly_recurrence')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        event_image = request.data.get('event_image')
        venue_id = request.data.get('venue')

        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

        open_mic = OpenMic.objects.create(
            user=request.user,
            event_title=event_title,
            recurrence=recurrence,
            weekly_recurrence=weekly_recurrence,
            monthly_recurrence=monthly_recurrence,
            start_time=start_time,
            end_time=end_time,
            event_image=event_image,
            venue=venue
        )

        serializer = OpenMicSerializer(open_mic, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        try:

            open_mic = OpenMic.objects.get(pk=pk)

            self.check_object_permissions(request, open_mic)

            serializer = OpenMicWriteSerializer(data=request.data)
            if serializer.is_valid():
                venue_id = request.data.get('venue_id')
                try:
                    venue = Venue.objects.get(pk=venue_id)
                except Venue.DoesNotExist:
                    return Response({'error': 'Venue not found'}, status=status.HTTP_400_BAD_REQUEST)

                open_mic.event_title = serializer.validated_data['event_title']
                open_mic.recurrence = serializer.validated_data['recurrence']
                open_mic.weekly_recurrence = serializer.validated_data['weekly_recurrence']
                open_mic.monthly_recurrence = serializer.validated_data['monthly_recurrence']
                open_mic.start_time = serializer.validated_data['start_time']
                open_mic.end_time = serializer.validated_data['end_time']
                open_mic.event_image = serializer.validated_data['event_image']
                open_mic.venue = venue
                open_mic.save()

                serializer = OpenMicSerializer(open_mic, context={'request': request})
                return Response(status=status.HTTP_204_NO_CONTENT)
            
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        
        except OpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def destroy(self, request, pk=None):
        try:
            open_mic = OpenMic.objects.get(pk=pk)
            if open_mic.user.id == request.auth.user.id:

                self.check_object_permissions(request, open_mic)
                open_mic.delete()

                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'message': 'You do not own that open mic'}, status=status.HTTP_403_FORBIDDEN)
        except OpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)