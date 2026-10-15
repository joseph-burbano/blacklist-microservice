"""Punto de entrada WSGI del microservicio."""

import os

from app import create_app


application = create_app()


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
