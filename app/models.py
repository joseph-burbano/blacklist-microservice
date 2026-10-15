"""Modelo persistido de la lista negra global."""

from datetime import datetime, timezone

from app import db


class BlacklistEntry(db.Model):
    __tablename__ = "blacklist_entries"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), nullable=False, unique=True, index=True)
    app_uuid = db.Column(db.String(36), nullable=False)
    blocked_reason = db.Column(db.String(255), nullable=True)
    source_ip = db.Column(db.String(45), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
