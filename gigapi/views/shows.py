from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers
from gigapi.models import Show
from .clients import Client, ClientSerializer

class ShowSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    client = ClientSerializer()

    def get_is_owner(self, obj):
        # Check if the authenticated user is the owner
        return self.context['request'].user == obj.user
    
    class Meta:
        model = Show
        fields = ['id', 'client', 'is_owner', 'event_title', 'poster_img', 'date', 'start_time', 'end_time']

class ShowWriteSerializer(serializers.ModelSerializer):
    client = serializers.ListField(child=serializers.PrimaryKeyRelatedField(queryset=Client.objects.all()), required=False)

    class Meta:
        model = Show
        fields = ['client', 'event_title', 'poster_img', 'date', 'start_time', 'end_time']


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
        # Get the data from the client's JSON payload
        client_id = request.data.get('client_id')
        poster_img = request.data.get('poster_img')
        date = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_400_BAD_REQUEST)

        show = Show.objects.create(
            client=client,
            poster_img=poster_img,
            date=date,
            start_time=start_time,
            end_time=end_time
        )

        serializer = ShowSerializer(show, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
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
        try:
            show = Show.objects.get(pk=pk)
            self.check_object_permissions(request, show)
            show.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Show.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)