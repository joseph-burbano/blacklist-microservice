"""Configuración de Flask y sus extensiones."""

import os

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

from version import VERSION


db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()


def create_app(test_config=None):
    """Construye la aplicación sin crear tablas durante el arranque WSGI."""
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY"),
        JWT_ACCESS_TOKEN_EXPIRES=False,
    )
    if test_config:
        app.config.update(test_config)

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL es obligatoria")
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY es obligatoria")

    try:
        proxy_count = int(os.environ.get("TRUSTED_PROXY_COUNT", "0"))
    except ValueError as exc:
        raise RuntimeError("TRUSTED_PROXY_COUNT debe ser 0 o 1") from exc
    if proxy_count not in (0, 1):
        raise RuntimeError("TRUSTED_PROXY_COUNT debe ser 0 o 1")
    if proxy_count:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count)

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(status="ok", version=VERSION)

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify(message="Token de autorización requerido o inválido."), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify(message="Token de autorización requerido o inválido."), 401

    @jwt.expired_token_loader
    def expired_token(_token):
        return jsonify(message="Token de autorización requerido o inválido."), 401

    from app.resources import BlacklistCollection, BlacklistItem

    api = Api(app)
    api.add_resource(BlacklistCollection, "/blacklists")
    api.add_resource(BlacklistItem, "/blacklists/<string:email>")
    return app
