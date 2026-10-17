"""Pruebas del contrato HTTP y los datos almacenados."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models import BlacklistEntry


class BlacklistApiTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "JWT_SECRET_KEY": "test-only-secret",
            }
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.token = create_access_token(identity="test-client", expires_delta=False)
        self.auth = {"Authorization": "Bearer {}".format(self.token)}
        self.valid = {
            "email": "  Person@Example.com  ",
            "app_uuid": "33154f55-2a0a-4dd4-876a-bc84d5f1467f",
            "blocked_reason": "Solicitud del área legal",
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_health_is_public_and_reports_version(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok", "version": "v1"})

    def test_post_persists_normalized_email_ip_and_timestamp(self):
        response = self.client.post(
            "/blacklists", json=self.valid,
            headers={**self.auth, "X-Forwarded-For": "198.51.100.9"},
            environ_base={"REMOTE_ADDR": "203.0.113.20"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["email"], "person@example.com")
        entry = BlacklistEntry.query.one()
        self.assertEqual(entry.email, "person@example.com")
        self.assertEqual(entry.app_uuid, self.valid["app_uuid"])
        self.assertEqual(entry.blocked_reason, self.valid["blocked_reason"])
        self.assertEqual(entry.source_ip, "203.0.113.20")
        self.assertLess(abs((datetime.utcnow() - entry.created_at).total_seconds()), 10)

    def test_get_found_and_not_found(self):
        self.client.post("/blacklists", json=self.valid, headers=self.auth)
        found = self.client.get("/blacklists/Person@Example.com", headers=self.auth)
        missing = self.client.get("/blacklists/absent@example.com", headers=self.auth)
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.get_json(), {
            "email": "person@example.com", "blacklisted": True,
            "blocked_reason": "Solicitud del área legal",
        })
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.get_json(), {
            "email": "absent@example.com", "blacklisted": False,
            "blocked_reason": None,
        })

    def test_duplicate_is_conflict(self):
        first = self.client.post("/blacklists", json=self.valid, headers=self.auth)
        second = self.client.post("/blacklists", json=self.valid, headers=self.auth)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(BlacklistEntry.query.count(), 1)

    def test_optional_reason_and_unknown_fields(self):
        without_reason = {key: value for key, value in self.valid.items()
                          if key != "blocked_reason"}
        response = self.client.post(
            "/blacklists", json=without_reason, headers=self.auth
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(BlacklistEntry.query.one().blocked_reason)

        with_unknown = {**self.valid, "unexpected": "value"}
        response = self.client.post(
            "/blacklists", json=with_unknown, headers=self.auth
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("unexpected", response.get_json()["errors"])

    def test_required_fields_and_limits(self):
        cases = (
            ({"app_uuid": self.valid["app_uuid"]}, "email"),
            ({"email": "a@example.com"}, "app_uuid"),
            ({**self.valid, "app_uuid": "bad-uuid"}, "app_uuid"),
            ({**self.valid, "blocked_reason": "x" * 256}, "blocked_reason"),
            ({**self.valid, "email": "not-an-email"}, "email"),
        )
        for body, field in cases:
            with self.subTest(field=field, body=body):
                response = self.client.post(
                    "/blacklists", json=body, headers=self.auth
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.get_json()["errors"])

    def test_invalid_json_and_lookup_email(self):
        bad_body = self.client.post(
            "/blacklists", data="not json", headers=self.auth,
            content_type="application/json",
        )
        bad_lookup = self.client.get("/blacklists/not-an-email", headers=self.auth)
        self.assertEqual(bad_body.status_code, 400)
        self.assertIn("body", bad_body.get_json()["errors"])
        self.assertEqual(bad_lookup.status_code, 400)

    def test_both_resources_require_valid_bearer(self):
        for method, path in (("post", "/blacklists"),
                             ("get", "/blacklists/a@example.com")):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                with self.subTest(method=method, headers=headers):
                    response = getattr(self.client, method)(path, headers=headers)
                    self.assertEqual(response.status_code, 401)

        expired = create_access_token(
            identity="test-client", expires_delta=timedelta(seconds=-1)
        )
        response = self.client.get(
            "/blacklists/a@example.com",
            headers={"Authorization": "Bearer {}".format(expired)},
        )
        self.assertEqual(response.status_code, 401)

    def test_only_one_configured_proxy_hop_is_trusted(self):
        with patch.dict("os.environ", {"TRUSTED_PROXY_COUNT": "1"}):
            proxy_app = create_app(
                {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                 "JWT_SECRET_KEY": "test-only-secret"}
            )
        with proxy_app.app_context():
            db.create_all()
            token = create_access_token(identity="test-client", expires_delta=False)
            response = proxy_app.test_client().post(
                "/blacklists",
                json=self.valid,
                headers={
                    "Authorization": "Bearer {}".format(token),
                    "X-Forwarded-For": "198.51.100.9, 203.0.113.30",
                },
                environ_base={"REMOTE_ADDR": "10.0.0.5"},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(BlacklistEntry.query.one().source_ip, "203.0.113.30")
            db.session.remove()
            db.drop_all()

    def test_beanstalk_two_proxy_hops_keep_client_ip(self):
        # En Beanstalk la petición pasa por el ALB y luego por nginx; nginx
        # agrega la IP del ALB al final de X-Forwarded-For.
        with patch.dict("os.environ", {"TRUSTED_PROXY_COUNT": "2"}):
            proxy_app = create_app(
                {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                 "JWT_SECRET_KEY": "test-only-secret"}
            )
        with proxy_app.app_context():
            db.create_all()
            token = create_access_token(identity="test-client", expires_delta=False)
            response = proxy_app.test_client().post(
                "/blacklists",
                json=self.valid,
                headers={
                    "Authorization": "Bearer {}".format(token),
                    "X-Forwarded-For": "198.51.100.9, 172.31.13.128",
                },
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(BlacklistEntry.query.one().source_ip, "198.51.100.9")
            db.session.remove()
            db.drop_all()

    def test_invalid_proxy_count_is_rejected(self):
        for value in ("3", "-1", "abc"):
            with self.subTest(value=value):
                with patch.dict("os.environ", {"TRUSTED_PROXY_COUNT": value}):
                    with self.assertRaises(RuntimeError):
                        create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                                    "JWT_SECRET_KEY": "test-only-secret"})


class ProductionErrorHandlingTest(unittest.TestCase):
    """Sin TESTING, Flask-RESTful no debe convertir los errores de JWT en 500."""

    def setUp(self):
        self.app = create_app(
            {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
             "JWT_SECRET_KEY": "test-only-secret"}
        )
        self.client = self.app.test_client()

    def test_missing_or_invalid_token_is_401(self):
        for method, path in (("post", "/blacklists"),
                             ("get", "/blacklists/a@example.com")):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                with self.subTest(method=method, headers=headers):
                    response = getattr(self.client, method)(path, headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(
                        response.get_json(),
                        {"message": "Token de autorización requerido o inválido."},
                    )


if __name__ == "__main__":
    unittest.main()
