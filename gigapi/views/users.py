import os

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.http import HttpResponseServerError
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """JSON serializer for Users

    Arguments:
        serializers
    """
    class Meta:
        model = User
        url = serializers.HyperlinkedIdentityField(
            view_name='user',
            lookup_field = 'id'
        )
        fields = ('id', 'url', 'username', 'password', 'first_name', 'last_name', 'email', 'is_active', 'date_joined')


@method_decorator(csrf_exempt, name='dispatch')
class Users(ViewSet):
    permission_classes = [AllowAny]
    """Users for Gig Gazette
    Purpose: Allow a user to communicate with the Gig Gazette database to GET PUT POST and DELETE Users.
    Methods: GET PUT(id) POST
"""
    def login_user(self, request):
        '''Handles the authentication of a manager
            Method arguments:
              request -- The full HTTP request object
        '''

        username = request.data['username']
        password = request.data['password']

        authenticated_user = authenticate(username=username, password=password)

        if authenticated_user is not None:
            token = Token.objects.get(user=authenticated_user)
            return Response({'valid': True, 'token': token.key, 'id': authenticated_user.id})
        else:
            return Response({'valid': False})


    def retrieve(self, request, pk=None):
        """Handle GET requests for single customer
        Purpose: Allow a user to communicate with the Gig Gazette database to retrieve  one user
        Methods:  GET
        Returns:
            Response -- JSON serialized customer instance
        """
        try:
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user, context={'request': request})
            return Response(serializer.data)
        except Exception as ex:
            return HttpResponseServerError(ex)



    def register(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        token = Token.objects.create(user=user)
        return Response({'token': token.key, 'id': user.id}, status=status.HTTP_201_CREATED)

    def list(self, request):
        """Handle GET requests to user resource"""
        users = User.objects.all()
        serializer = UserSerializer(
            users, many=True, context={'request': request})
        return Response(serializer.data)

    def request_password_reset(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
            reset_link = f"{frontend_url}/reset-password/{uid}/{token}"

            send_mail(
                subject='Reset your Gig Gazette password',
                message=f'Click the link below to reset your password:\n\n{reset_link}\n\nThis link expires after 24 hours.',
                from_email=os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@giggazette.com'),
                recipient_list=[email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass

        return Response({'message': 'If that email is registered, a reset link has been sent.'})

    def confirm_password_reset(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response({'error': 'uid, token, and new_password are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'error': 'Reset link is invalid or has expired'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password reset successfully'})