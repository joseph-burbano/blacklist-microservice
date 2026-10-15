"""Comandos manuales de preparación de la base y del token compartido."""

import argparse

from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models import BlacklistEntry  # noqa: F401: registra el modelo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init-db", "issue-token"))
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        if args.command == "init-db":
            db.create_all()
            print("Esquema preparado.")
        else:
            print(create_access_token(identity="internal-client", expires_delta=False))


if __name__ == "__main__":
    main()
