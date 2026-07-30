from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Member
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['sid', 'name', 'email', 'status', 'join_date', 'role']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = Member.USERNAME_FIELD 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        if 'username' in self.initial_data:
            self.initial_data[self.username_field] = self.initial_data.pop('username')[0] if isinstance(self.initial_data.get('username'), list) else self.initial_data.get('username')

    def validate(self, attrs):
        data = super().validate(attrs)
        data['name'] = self.user.name
        data['sid'] = self.user.sid
        data['role'] = self.user.role
        
        return data

class UserCreateSerializer(serializers.ModelSerializer):
    # AUTH_PASSWORD_VALIDATORS 는 set_password() 가 호출하지 않으므로
    # 시리얼라이저에서 명시적으로 걸어야 실제로 적용된다.
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Member
        fields = ['sid', 'name', 'email', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Member.objects.create_user(
            sid=validated_data['sid'],
            username=str(validated_data['sid']), 
            name=validated_data['name'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'UNDERGRADUATE')
        )
        return user