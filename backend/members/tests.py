from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import Member


class AuthenticationSecurityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = "Separate-random-passphrase-728!"
        self.member = Member.objects.create_user(
            sid=20260001, name="Test Reader", email="reader@example.test",
            password=self.password,
        )

    def tokens(self):
        response = self.client.post("/api/token/", {
            "sid": self.member.sid, "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_blocked_member_cannot_login_or_use_existing_tokens(self):
        for member_status in (Member.Status.SUSPENDED, Member.Status.WITHDRAWN, Member.Status.DORMANT):
            with self.subTest(status=member_status):
                self.member.status = Member.Status.ACTIVE
                self.member.save()
                tokens = self.tokens()
                self.member.status = member_status
                self.member.save()
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
                self.assertEqual(self.client.get("/api/loans/").status_code, 401)
                self.client.credentials()
                self.assertEqual(self.client.post("/api/token/refresh/", {
                    "refresh": tokens["refresh"],
                }).status_code, 401)
                self.assertEqual(self.client.post("/api/token/", {
                    "sid": self.member.sid, "password": self.password,
                }).status_code, 401)

    def test_password_change_revokes_access_and_refresh(self):
        tokens = self.tokens()
        self.member.set_password("A-new-unrelated-password-920!")
        self.member.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.get("/api/loans/").status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post("/api/token/refresh/", {
            "refresh": tokens["refresh"],
        }).status_code, 401)

    def test_refresh_is_rotated_and_cannot_be_replayed(self):
        tokens = self.tokens()
        refreshed = self.client.post("/api/token/refresh/", {"refresh": tokens["refresh"]})
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("refresh", refreshed.data)
        self.assertNotEqual(refreshed.data["refresh"], tokens["refresh"])
        self.assertEqual(self.client.post("/api/token/refresh/", {
            "refresh": tokens["refresh"],
        }).status_code, 401)
        self.assertEqual(self.client.post("/api/token/refresh/", {
            "refresh": refreshed.data["refresh"],
        }).status_code, 200)

    def test_logout_revokes_refresh_and_is_idempotent(self):
        tokens = self.tokens()
        for _ in range(2):
            self.assertEqual(self.client.post("/api/token/logout/", {
                "refresh": tokens["refresh"],
            }).status_code, 204)
        self.assertEqual(self.client.post("/api/token/refresh/", {
            "refresh": tokens["refresh"],
        }).status_code, 401)

    def test_deleted_user_refresh_is_rejected_without_server_error(self):
        tokens = self.tokens()
        self.member.delete()
        self.assertEqual(self.client.post("/api/token/refresh/", {
            "refresh": tokens["refresh"],
        }).status_code, 401)

    def test_missing_password_does_not_default_to_student_id(self):
        member = Member.objects.create_user(
            sid=20260002, name="No password", email="unusable@example.test",
        )
        self.assertFalse(member.has_usable_password())
        self.assertFalse(member.check_password(str(member.sid)))

    def test_signup_cannot_self_assign_extended_loan_privileges(self):
        for role in (Member.Role.PROFESSOR, Member.Role.GRADUATE):
            with self.subTest(role=role):
                response = self.client.post("/api/members/", {
                    "sid": 20260002, "name": "New Reader", "email": "new@example.test",
                    "password": self.password, "role": role,
                })
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Member.objects.filter(sid=20260002).exists())

    def test_signup_validates_similarity_and_preserves_password_whitespace(self):
        payload = {"sid": 20260003, "name": "UniqueReaderIdentifier", "email": "new@example.test"}
        response = self.client.post("/api/members/", {**payload, "password": payload["name"]})
        self.assertEqual(response.status_code, 400)
        password = "  A-long-random-passphrase-91!  "
        response = self.client.post("/api/members/", {**payload, "password": password})
        self.assertEqual(response.status_code, 201)
        member = Member.objects.get(sid=payload["sid"])
        self.assertTrue(member.check_password(password))
        self.assertEqual(member.role, Member.Role.UNDERGRADUATE)
        login = self.client.post("/api/token/", {"sid": member.sid, "password": password})
        self.assertEqual(login.status_code, 200)

    def test_member_records_are_private(self):
        self.assertEqual(self.client.get("/api/members/").status_code, 401)
        tokens = self.tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.get("/api/members/").status_code, 403)

    def test_logout_handles_untrusted_json_shapes_without_server_error(self):
        for payload in ([], 42, "token", {"refresh": []}, {"refresh": "invalid"}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/token/logout/", payload, format="json")
                self.assertEqual(response.status_code, 204)

    def test_legacy_login_alias_and_invalid_student_id(self):
        response = self.client.post("/api/token/", {
            "username": str(self.member.sid), "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        response = self.client.post("/api/token/", {"sid": "not-a-number", "password": self.password})
        self.assertEqual(response.status_code, 400)

    def test_blocked_staff_cannot_login_to_admin(self):
        self.member.is_staff = True
        self.member.save()
        self.assertTrue(self.client.login(sid=self.member.sid, password=self.password))
        self.client.logout()
        self.member.status = Member.Status.SUSPENDED
        self.member.save()
        self.assertFalse(self.client.login(sid=self.member.sid, password=self.password))

    def test_login_rejects_non_object_json_without_server_error(self):
        for payload in (42, "token", ["username"], []):
            with self.subTest(payload=payload):
                response = self.client.post("/api/token/", payload, format="json")
                self.assertEqual(response.status_code, 400)
