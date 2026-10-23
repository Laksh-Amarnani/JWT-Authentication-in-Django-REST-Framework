import requests
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer

RANDOM_USER_URL = 'https://randomuser.me/api/?results=3'


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class ProtectedView(APIView):
    # No permission_classes here: IsAuthenticated is the default in settings.py.

    def get(self, request):
        # Django's default cache is local memory, so no CACHES setting is needed.
        users = cache.get('random_users')
        if users is None:
            try:
                response = requests.get(RANDOM_USER_URL, timeout=10)
                response.raise_for_status()
                users = response.json()['results']
            except (requests.RequestException, KeyError):
                return Response(
                    {'detail': 'Could not get data from the Random User API. Try again later.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            cache.set('random_users', users, 60)

        return Response({'you': request.user.username, 'users': users})
