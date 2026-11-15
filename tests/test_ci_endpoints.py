"""Escenarios independientes por endpoint que se ejecutan en CodeBuild."""

import unittest

from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models import BlacklistEntry
from version import VERSION


class ApiEndpointCase(unittest.TestCase):
    """Prepara una base aislada y un JWT de prueba para cada escenario."""

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "ci-test-only-secret",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        token = create_access_token(identity="ci-test", expires_delta=False)
        self.auth = {"Authorization": "Bearer " + token}
        self.payload = {
            "email": " Person@Example.com ",
            "app_uuid": "33154f55-2a0a-4dd4-876a-bc84d5f1467f",
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()


class HealthEndpointTest(ApiEndpointCase):
    def test_health_is_public_and_reports_version(self):
        """GET /health responde 200 y versión sin autenticación."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok", "version": VERSION})


class PostBlacklistsEndpointTest(ApiEndpointCase):
    def test_post_creates_normalized_entry(self):
        """POST /blacklists responde 201 y persiste el email normalizado."""
        response = self.client.post("/blacklists", json=self.payload, headers=self.auth)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["email"], "person@example.com")
        self.assertEqual(BlacklistEntry.query.one().email, "person@example.com")

    def test_post_rejects_missing_token(self):
        """POST /blacklists responde 401 cuando falta el JWT."""
        response = self.client.post("/blacklists", json=self.payload)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(BlacklistEntry.query.count(), 0)


class GetBlacklistsEndpointTest(ApiEndpointCase):
    def test_get_reports_existing_email(self):
        """GET /blacklists/<email> responde 200 y true para un email guardado."""
        self.client.post("/blacklists", json=self.payload, headers=self.auth)
        response = self.client.get("/blacklists/Person@Example.com", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["blacklisted"])
        self.assertEqual(response.get_json()["email"], "person@example.com")

    def test_get_reports_absent_email(self):
        """GET /blacklists/<email> responde 200 y false si no existe."""
        response = self.client.get("/blacklists/absent@example.com", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["blacklisted"])

    def test_get_rejects_missing_token(self):
        """GET /blacklists/<email> responde 401 cuando falta el JWT."""
        response = self.client.get("/blacklists/a@example.com")
        self.assertEqual(response.status_code, 401)
