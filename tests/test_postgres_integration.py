"""Prueba opcional contra un PostgreSQL dedicado a integración."""

import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models import BlacklistEntry


@unittest.skipUnless(
    os.environ.get("INTEGRATION_DATABASE_URL"),
    "Definir INTEGRATION_DATABASE_URL para probar PostgreSQL",
)
class PostgreSqlIntegrationTest(unittest.TestCase):
    def test_post_get_and_utc_timestamp(self):
        with patch.dict("os.environ", {"TRUSTED_PROXY_COUNT": "0"}):
            app = create_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": os.environ["INTEGRATION_DATABASE_URL"],
                    "JWT_SECRET_KEY": "integration-test-only-secret",
                }
            )
        email = "integration-{}@example.com".format(uuid4().hex)
        with app.app_context():
            self.assertEqual(db.engine.dialect.name, "postgresql")
            token = create_access_token(identity="integration-client")
            auth = {"Authorization": "Bearer {}".format(token)}
            client = app.test_client()
            try:
                created = client.post(
                    "/blacklists",
                    json={"email": email, "app_uuid": str(uuid4())},
                    headers=auth, environ_base={"REMOTE_ADDR": "203.0.113.42"},
                )
                self.assertEqual(created.status_code, 201, created.get_json())
                found = client.get("/blacklists/{}".format(email), headers=auth)
                self.assertEqual(found.status_code, 200)
                self.assertTrue(found.get_json()["blacklisted"])
                entry = BlacklistEntry.query.filter_by(email=email).one()
                self.assertEqual(entry.source_ip, "203.0.113.42")
                self.assertEqual(entry.created_at.utcoffset().total_seconds(), 0)
            finally:
                BlacklistEntry.query.filter_by(email=email).delete()
                db.session.commit()
                db.session.remove()


if __name__ == "__main__":
    unittest.main()
