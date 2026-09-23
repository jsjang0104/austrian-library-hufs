import os
from pathlib import Path
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
# Fail closed unless local development is explicitly enabled.
DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY")
if not DEBUG and (
    len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured("SECRET_KEY must be a strong, unique production secret.")

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="ohjigo-library.onrender.com,ohjigo-library-library.onrender.com",
    cast=Csv(),
)
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "common",
    "members",
    "library",
    "manager",
    'import_export',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # 정적 파일용
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Preview domains must be individually opted in; never trust all vercel.app sites.
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="https://austrian-library-hufs.vercel.app", cast=Csv(),
)
if DEBUG:
    CORS_ALLOWED_ORIGINS += ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_URLS_REGEX = r"^/api/.*$"
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, '..', 'frontend', 'dist')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
db_url = config("DATABASE_URL", default=None)

if db_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=db_url,
            conn_max_age=0,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

REST_FRAMEWORK = {
    # 기본은 차단. 공개가 필요한 뷰에서만 명시적으로 완화한다.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'members.authentication.ActiveMemberJWTAuthentication',
        'members.authentication.ActiveMemberSessionAuthentication',
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 인증 및 AI 검색에만 요청 한도를 적용한다. 현재 기본 캐시는 프로세스별
    # LocMemCache이므로 여러 워커/인스턴스의 강한 제한은 외부 WAF/공유 캐시가 필요하다.
    "DEFAULT_THROTTLE_RATES": {
        "login": "15/min",
        "register": "20/hour",
        "refresh": "60/min",
        "logout": "60/min",
        "smart_search": "30/min",
    },
}

# 비밀번호 정책. 미설정 상태라 "1" 같은 비밀번호도 가입이 통과하고 있었다.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("username", "name", "email")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SIMPLE_JWT = {
    'TOKEN_OBTAIN_SERIALIZER': 'members.serializers.CustomTokenObtainPairSerializer',
    'USER_ID_FIELD': 'sid',
    'USER_ID_CLAIM': 'user_id',

    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'CHECK_REVOKE_TOKEN': True,
    'USER_AUTHENTICATION_RULE': 'members.authentication.active_member_rule',
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# 운영(HTTPS) 환경 보안 헤더. Render 가 TLS 를 종료하고 X-Forwarded-Proto 를 넘긴다.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

AUTHENTICATION_BACKENDS = ['members.authentication.ActiveMemberBackend']
AUTH_USER_MODEL = 'members.Member'
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

HF_API_TOKEN = config("HF_API_TOKEN", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "library": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
