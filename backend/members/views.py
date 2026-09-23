from collections.abc import Mapping
from rest_framework import viewsets, generics, permissions, serializers
from .models import Member
from .serializers import MemberSerializer, UserCreateSerializer, CustomTokenObtainPairSerializer, ActiveMemberTokenRefreshSerializer, LogoutRequestSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.throttling import ScopedRateThrottle
from common.permissions import CreateOnlyOrStaff


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    lookup_field = 'sid'
    # 가입(POST)만 공개. 회원 목록/상세는 스태프 전용.
    permission_classes = [CreateOnlyOrStaff]
    throttle_scope = 'register'

    def get_throttles(self):
        # 가입 요청에만 register 레이트를 적용한다.
        if self.action == 'create':
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

class TokenObtainRequestSerializer(serializers.Serializer):
    sid = serializers.IntegerField()
    password = serializers.CharField()

@extend_schema(
    request=TokenObtainRequestSerializer,
    summary="Custom Token Obtain",
    description="Takes a set of user credentials and returns an access and refresh JSON web token pair to prove the authentication of those credentials."
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class RegistrationView(generics.CreateAPIView):
    queryset = Member.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"



class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = ActiveMemberTokenRefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refresh"


class LogoutView(APIView):
    # Possession of the refresh token is sufficient to revoke that token.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "logout"

    @extend_schema(request=LogoutRequestSerializer, responses={204: None})
    def post(self, request):
        token = request.data.get("refresh") if isinstance(request.data, Mapping) else None
        if isinstance(token, str) and len(token) <= 4096:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass  # Expired/already revoked tokens are already logged out.
        return Response(status=204)
