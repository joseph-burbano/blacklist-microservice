"""Generate the build artifacts consumed by CodePipeline CodeDeployToECS."""

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "IMAGE_URI",
    "AWS_DEFAULT_REGION",
    "ECS_TASK_EXECUTION_ROLE_ARN",
    "DATABASE_URL_SECRET_ARN",
    "JWT_SECRET_KEY_SECRET_ARN",
    "ECS_LOG_GROUP",
)


def main():
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing build configuration: " + ", ".join(missing))

    image_uri = os.environ["IMAGE_URI"]
    region = os.environ["AWS_DEFAULT_REGION"]
    container = {
        "name": "blacklist",
        "image": "<IMAGE1_NAME>",
        "essential": True,
        "portMappings": [{"containerPort": 5000, "hostPort": 5000, "protocol": "tcp"}],
        "environment": [
            {"name": "TRUSTED_PROXY_COUNT", "value": os.environ.get("TRUSTED_PROXY_COUNT", "1")},
        ],
        "secrets": [
            {"name": "DATABASE_URL", "valueFrom": os.environ["DATABASE_URL_SECRET_ARN"]},
            {"name": "JWT_SECRET_KEY", "valueFrom": os.environ["JWT_SECRET_KEY_SECRET_ARN"]},
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": os.environ["ECS_LOG_GROUP"],
                "awslogs-region": region,
                "awslogs-stream-prefix": "blacklist",
            },
        },
    }
    task = {
        "family": "blacklist",
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "256",
        "memory": "512",
        "executionRoleArn": os.environ["ECS_TASK_EXECUTION_ROLE_ARN"],
        "containerDefinitions": [container],
    }
    if os.environ.get("ECS_TASK_ROLE_ARN"):
        task["taskRoleArn"] = os.environ["ECS_TASK_ROLE_ARN"]

    (ROOT / "taskdef.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (ROOT / "imageDetail.json").write_text(
        json.dumps({"ImageURI": image_uri}, indent=2) + "\n", encoding="utf-8"
    )
    print("Generated taskdef.json and imageDetail.json for", image_uri)


if __name__ == "__main__":
    main()
