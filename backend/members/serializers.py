from rest_framework import serializers
from .models import Member
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'status', 'join_date', 'role']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = Member.USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)
        data['name'] = self.user.name
        data['email'] = self.user.email
        data['role'] = self.user.role

        return data

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'password', 'role']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return Member.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            role=validated_data.get('role', 'UNDERGRADUATE')
        )
