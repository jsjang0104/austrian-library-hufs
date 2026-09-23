"""Isolated security tests: never load deployment secrets or a production DB."""
import os
import tempfile

from decouple import Config, RepositoryEmpty

# config.settings imports decouple.config. Ignore local .env files during tests.
import decouple

decouple.config = Config(RepositoryEmpty())
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-only-key-never-use-in-production-" + "x" * 32
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from .settings import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
MEDIA_ROOT = tempfile.mkdtemp(prefix="austrian-library-tests-")
HF_API_TOKEN = ""
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECURE_SSL_REDIRECT = False

STATIC_ROOT = tempfile.mkdtemp(prefix="austrian-library-static-tests-")
