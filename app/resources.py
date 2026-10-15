"""Recursos REST de consulta y registro de emails bloqueados."""

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import BlacklistEntry
from app.schemas import create_schema, email_schema, normalize_email


def validation_error(errors):
    return {"message": "Datos inválidos.", "errors": errors}, 400


class BlacklistCollection(Resource):
    @jwt_required
    def post(self):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return validation_error({"body": ["Se requiere un objeto JSON."]})
        try:
            data = create_schema.load(payload)
        except ValidationError as exc:
            return validation_error(exc.messages)

        entry = BlacklistEntry(
            email=data["email"],
            app_uuid=str(data["app_uuid"]),
            blocked_reason=data.get("blocked_reason"),
            source_ip=request.remote_addr,
        )
        db.session.add(entry)
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            original = exc.orig
            unique_email = (
                getattr(original, "pgcode", None) == "23505"
                or "UNIQUE constraint failed: blacklist_entries.email" in str(original)
            )
            if unique_email:
                return {"message": "El email ya está en la lista negra."}, 409
            raise
        return {
            "message": "Email agregado a la lista negra.",
            "email": entry.email,
        }, 201


class BlacklistItem(Resource):
    @jwt_required
    def get(self, email):
        normalized = normalize_email(email)
        try:
            email_schema.load({"email": normalized})
        except ValidationError as exc:
            return validation_error(exc.messages)

        entry = BlacklistEntry.query.filter_by(email=normalized).first()
        return {
            "email": normalized,
            "blacklisted": entry is not None,
            "blocked_reason": entry.blocked_reason if entry else None,
        }, 200
