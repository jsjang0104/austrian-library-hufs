from collections.abc import Mapping
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import Member
from .authentication import active_member_rule


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['sid', 'name', 'email', 'status', 'join_date', 'role']
        read_only_fields = ['sid', 'join_date']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = Member.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        # Normalize the legacy username alias without mutating request.data.
        if isinstance(kwargs.get('data'), Mapping):
            data = kwargs['data'].copy()
            if self.username_field not in data and 'username' in data:
                data[self.username_field] = data['username']
            kwargs['data'] = data
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False
        self.fields[self.username_field] = serializers.IntegerField(min_value=1, max_value=2147483647, write_only=True)

    def validate(self, attrs):
        data = super().validate(attrs)
        data.update(name=self.user.name, sid=self.user.sid, role=self.user.role)
        return data


class ActiveMemberTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])
        try:
            user = Member.objects.get(pk=refresh.get(api_settings.USER_ID_CLAIM))
        except (Member.DoesNotExist, ValueError, TypeError, OverflowError):
            raise AuthenticationFailed("사용할 수 없는 토큰입니다.")
        if not active_member_rule(user):
            raise AuthenticationFailed("사용할 수 없는 계정입니다.")
        if api_settings.CHECK_REVOKE_TOKEN and refresh.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed("비밀번호가 변경되었습니다. 다시 로그인해주세요.")
        return super().validate(attrs)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    sid = serializers.IntegerField(min_value=1, max_value=2147483647)

    class Meta:
        model = Member
        fields = ['sid', 'name', 'email', 'password', 'role']

    def validate_sid(self, value):
        if Member.objects.filter(sid=value).exists():
            raise serializers.ValidationError("이미 등록된 학번입니다.")
        return value

    def validate_role(self, value):
        if value != Member.Role.UNDERGRADUATE:
            raise serializers.ValidationError("대학원생·교수 대출 권한은 관리자 확인 후 부여됩니다.")
        return value

    def validate(self, attrs):
        candidate = Member(**{key: value for key, value in attrs.items() if key != 'password'})
        candidate.username = str(candidate.sid)
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated_data):
        return Member.objects.create_user(**validated_data)


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, max_length=4096)
