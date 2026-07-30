from rest_framework import viewsets, generics, permissions, serializers
from .models import Member
from .serializers import MemberSerializer, UserCreateSerializer, CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

class TokenObtainRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

@extend_schema(
    request=TokenObtainRequestSerializer,
    summary="Custom Token Obtain",
    description="Takes a set of user credentials and returns an access and refresh JSON web token pair to prove the authentication of those credentials."
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegistrationView(generics.CreateAPIView):
    queryset = Member.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny] 

