"""Keep API authentication documentation accurate for our stricter authenticators."""
from drf_spectacular.authentication import SessionScheme
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class ActiveMemberJWTScheme(SimpleJWTScheme):
    target_class = "members.authentication.ActiveMemberJWTAuthentication"


class ActiveMemberSessionScheme(SessionScheme):
    target_class = "members.authentication.ActiveMemberSessionAuthentication"
