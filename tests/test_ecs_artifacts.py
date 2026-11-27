"""Comprueba el contrato de secretos y monitoreo del artefacto ECS."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import render_ecs_artifacts


class RenderEcsArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            "IMAGE_URI": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/blacklist:abc123",
            "AWS_DEFAULT_REGION": "eu-west-1",
            "ECS_TASK_EXECUTION_ROLE_ARN": "arn:aws:iam::123456789012:role/ecs-execution",
            "DATABASE_URL_SECRET_ARN": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:database",
            "JWT_SECRET_KEY_SECRET_ARN": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:jwt",
            "NEW_RELIC_LICENSE_KEY_SECRET_ARN": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:newrelic",
            "ECS_LOG_GROUP": "/ecs/blacklist",
        }

    def test_requires_license_secret_arn(self):
        env = dict(self.env)
        del env["NEW_RELIC_LICENSE_KEY_SECRET_ARN"]
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(SystemExit, "NEW_RELIC_LICENSE_KEY_SECRET_ARN"):
                render_ecs_artifacts.main()

    def test_renders_secret_reference_and_cloud_app_name(self):
        env = dict(self.env)
        env["NEW_RELIC_LICENSE_KEY"] = "license-key-value"
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", env, clear=True):
                with patch.object(render_ecs_artifacts, "ROOT", Path(directory)):
                    render_ecs_artifacts.main()
            task_path = Path(directory) / "taskdef.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))
            container = task["containerDefinitions"][0]
            secrets = {entry["name"]: entry["valueFrom"] for entry in container["secrets"]}
            environment = {entry["name"]: entry["value"] for entry in container["environment"]}
            self.assertEqual(secrets["NEW_RELIC_LICENSE_KEY"], self.env["NEW_RELIC_LICENSE_KEY_SECRET_ARN"])
            self.assertEqual(environment["NEW_RELIC_APP_NAME"], "blacklist-fargate")
            self.assertEqual(environment["NEW_RELIC_LOG"], "stdout")
            self.assertNotIn("NEW_RELIC_LICENSE_KEY", environment)
            self.assertNotIn("license-key-value", task_path.read_text(encoding="utf-8"))
            image = json.loads((Path(directory) / "imageDetail.json").read_text(encoding="utf-8"))
            self.assertEqual(image["ImageURI"], self.env["IMAGE_URI"])


if __name__ == "__main__":
    unittest.main()
