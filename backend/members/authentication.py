from django.contrib.auth.backends import ModelBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Member


def active_member_rule(user):
    return bool(user and user.is_active and user.status == Member.Status.ACTIVE)


class ActiveMemberJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not active_member_rule(user):
            raise AuthenticationFailed("사용할 수 없는 계정입니다.")
        return user


class ActiveMemberSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result and not active_member_rule(result[0]):
            raise AuthenticationFailed("사용할 수 없는 계정입니다.")
        return result


class ActiveMemberBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return active_member_rule(user)
