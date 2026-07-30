import os
from pathlib import Path
from decouple import config
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = config("DEBUG", default=True, cast=bool)
# 운영 환경에서는 SECRET_KEY 미설정 시 폴백하지 않고 즉시 실패시킨다.
# (JWT SIGNING_KEY 로도 쓰이므로 공개된 값으로 폴백되면 토큰 위조가 가능)
if DEBUG:
    SECRET_KEY = config("SECRET_KEY", default="django-insecure-fallback-key-123")
else:
    SECRET_KEY = config("SECRET_KEY")
# ---------------------------------------------------
if not DEBUG:
    ALLOWED_HOSTS = [
        'ohjigo-library.onrender.com',
        'ohjigo-library-library.onrender.com',
        'localhost',
        '127.0.0.1',
        '.onrender.com', 
    ]
else:
    ALLOWED_HOSTS = ['*']
# ---------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
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

# 전체 허용(*) 대신 배포 도메인과 로컬 개발 서버만 허용한다.
# Vercel 프리뷰 배포는 임의 서브도메인을 쓰므로 정규식으로 함께 허용.
CORS_ALLOWED_ORIGINS = [
    "https://austrian-library-hufs.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]
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
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', 
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 전역 스로틀은 걸지 않는다. 아래 레이트는 로그인/가입 뷰에 ScopedRateThrottle
    # 로만 적용된다. 전역으로 걸면 모든 요청이 캐시(=DB) 쓰기를 유발한다.
    # 캠퍼스 공용 IP 에서 여러 명이 동시에 쓰는 상황을 감안해 넉넉하게 잡았다.
    "DEFAULT_THROTTLE_RATES": {
        "login": "15/min",
        "register": "20/hour",
    },
}

# 비밀번호 정책. 미설정 상태라 "1" 같은 비밀번호도 가입이 통과하고 있었다.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SIMPLE_JWT = {
    'TOKEN_OBTAIN_SERIALIZER': 'members.serializers.CustomTokenObtainPairSerializer',
    'USER_ID_FIELD': 'sid', 
    'USER_ID_CLAIM': 'user_id',

    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
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