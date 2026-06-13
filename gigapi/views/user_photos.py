from rest_framework import serializers, status, viewsets
from rest_framework.response import Response

from gigapi.models import OpenMic, WritersRound, UserPhotoForOpenMic, UserPhotoForWritersRound


class UserPhotoForOpenMicSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPhotoForOpenMic
        fields = ['id', 'user', 'open_mic', 'user_image']


class UserPhotoForWritersRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPhotoForWritersRound
        fields = ['id', 'user', 'writers_round', 'user_image']


class UserPhotoForOpenMicViewSet(viewsets.ViewSet):

    def list(self, request):
        photos = UserPhotoForOpenMic.objects.all()
        open_mic_id = request.query_params.get('open_mic_id')
        if open_mic_id:
            photos = photos.filter(open_mic__id=open_mic_id)
        serializer = UserPhotoForOpenMicSerializer(photos, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        open_mic_id = request.data.get('open_mic')
        try:
            open_mic = OpenMic.objects.get(pk=open_mic_id)
        except OpenMic.DoesNotExist:
            return Response({'error': 'Open mic not found'}, status=status.HTTP_400_BAD_REQUEST)

        photo = UserPhotoForOpenMic.objects.create(
            user=request.user,
            open_mic=open_mic,
            user_image=request.data.get('user_image'),
        )

        serializer = UserPhotoForOpenMicSerializer(photo, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            photo = UserPhotoForOpenMic.objects.get(pk=pk)
        except UserPhotoForOpenMic.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if photo.user != request.user:
            return Response({'error': 'You do not own this photo'}, status=status.HTTP_403_FORBIDDEN)

        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserPhotoForWritersRoundViewSet(viewsets.ViewSet):

    def list(self, request):
        photos = UserPhotoForWritersRound.objects.all()
        writers_round_id = request.query_params.get('writers_round_id')
        if writers_round_id:
            photos = photos.filter(writers_round__id=writers_round_id)
        serializer = UserPhotoForWritersRoundSerializer(photos, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        writers_round_id = request.data.get('writers_round')
        try:
            writers_round = WritersRound.objects.get(pk=writers_round_id)
        except WritersRound.DoesNotExist:
            return Response({'error': 'Writers round not found'}, status=status.HTTP_400_BAD_REQUEST)

        photo = UserPhotoForWritersRound.objects.create(
            user=request.user,
            writers_round=writers_round,
            user_image=request.data.get('user_image'),
        )

        serializer = UserPhotoForWritersRoundSerializer(photo, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            photo = UserPhotoForWritersRound.objects.get(pk=pk)
        except UserPhotoForWritersRound.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if photo.user != request.user:
            return Response({'error': 'You do not own this photo'}, status=status.HTTP_403_FORBIDDEN)

        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
