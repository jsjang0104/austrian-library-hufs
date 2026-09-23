import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient


class DeploymentSecurityTests(SimpleTestCase):
    def test_cors_allows_only_the_library_origin(self):
        client = APIClient()
        for origin, allowed in (
            ("https://austrian-library-hufs.vercel.app", True),
            ("https://attacker.vercel.app", False),
            ("https://austrian-library-hufs.vercel.app.evil.example", False),
        ):
            with self.subTest(origin=origin):
                response = client.options(
                    "/api/token/", HTTP_ORIGIN=origin,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                )
                self.assertEqual(response.get("Access-Control-Allow-Origin"), origin if allowed else None)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["ohjigo-library.onrender.com"])
    def test_unknown_hosts_are_rejected(self):
        response = self.client.get("/api/", HTTP_HOST="attacker.onrender.com")
        self.assertEqual(response.status_code, 400)

    def test_production_defaults_reject_missing_or_weak_secret(self):
        script = (
            "import decouple; "
            "decouple.config = decouple.Config(decouple.RepositoryEmpty()); "
            "import config.settings as s; print(s.DEBUG)"
        )
        env = {key: value for key, value in os.environ.items() if key not in {"DEBUG", "SECRET_KEY", "DATABASE_URL"}}
        for key in (None, "django-insecure-fallback-key-123"):
            with self.subTest(secret="missing" if key is None else "weak"):
                scoped_env = dict(env)
                if key:
                    scoped_env["SECRET_KEY"] = key
                result = subprocess.run([sys.executable, "-c", script], cwd=settings.BASE_DIR, env=scoped_env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
        env["SECRET_KEY"] = "test-only-production-validation-" + "1234567890abcdefghij" * 2
        result = subprocess.run([sys.executable, "-c", script], cwd=settings.BASE_DIR, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")
