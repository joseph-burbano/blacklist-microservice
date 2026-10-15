"""Punto de entrada WSGI del microservicio."""

import os

from flask import Flask, jsonify

from version import VERSION


application = Flask(__name__)


@application.route("/health", methods=["GET"])
def health():
    """Respuesta básica para comprobar que el proceso está disponible."""
    return jsonify(status="ok", version=VERSION)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
