"""Validación y normalización del contrato JSON."""

from marshmallow import fields, pre_load, validate

from app import ma


def normalize_email(email):
    return email.strip().lower()


class BlacklistCreateSchema(ma.Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    app_uuid = fields.UUID(required=True)
    blocked_reason = fields.String(
        allow_none=True, validate=validate.Length(max=255)
    )

    @pre_load
    def normalize(self, data, **_kwargs):
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            return {**data, "email": normalize_email(data["email"])}
        return data


create_schema = BlacklistCreateSchema()
email_schema = ma.Schema.from_dict(
    {"email": fields.Email(required=True, validate=validate.Length(max=320))}
)()
