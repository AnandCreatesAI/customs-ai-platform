from django.contrib.auth import get_user_model, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import LoginSerializer, UserSerializer
from apps.authentication.throttling import LoginRateThrottle

User = get_user_model()

_INVALID_CREDENTIALS_DETAIL = 'Invalid email or password.'
_INACTIVE_USER_DETAIL = 'User account is inactive.'


class CsrfView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        return Response({'csrfToken': get_token(request)}, status=status.HTTP_200_OK)


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @method_decorator(csrf_protect)
    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = User.objects.normalize_email(serializer.validated_data['email'])
        password = serializer.validated_data['password']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'detail': _INVALID_CREDENTIALS_DETAIL},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {'detail': _INVALID_CREDENTIALS_DETAIL},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'detail': _INACTIVE_USER_DETAIL},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect)
    def post(self, request: Request, *args, **kwargs) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': _INACTIVE_USER_DETAIL},
                status=status.HTTP_403_FORBIDDEN,
            )
        logout(request)
        return Response({'success': True}, status=status.HTTP_200_OK)


class MeView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': _INACTIVE_USER_DETAIL},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
