from rest_framework import generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import CustomUserSerializer

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

class UserLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(UserLoginView, self).post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        return Response({'token': token.key, 'id': token.user_id})