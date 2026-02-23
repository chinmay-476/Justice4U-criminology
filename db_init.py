import os

from extensions import db
from models import MasterAuth
from werkzeug.security import generate_password_hash


def ensure_master_auth_seed():
    email = os.getenv('MASTER_AUTH_EMAIL', 'chinmaysahoo63715@gmail.com').strip().lower()
    password = os.getenv('MASTER_AUTH_PASSWORD', 'chin1987')
    if not email or not password:
        return

    try:
        record = MasterAuth.query.filter_by(email=email).first()
        password_hash = generate_password_hash(password)
        if record:
            record.password_hash = password_hash
            record.can_admin = True
            record.can_super_admin = True
            record.is_active = True
        else:
            db.session.add(
                MasterAuth(
                    email=email,
                    password_hash=password_hash,
                    can_admin=True,
                    can_super_admin=True,
                    is_active=True,
                )
            )
        db.session.commit()
    except Exception:
        db.session.rollback()


def run_startup_schema_checks():
    # Ensure new columns exist in existing DB (idempotent ALTERs)
    try:
        result = db.session.execute(
            db.text(
                """
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'accused'
                  AND COLUMN_NAME = 'pincode'
                """
            )
        ).scalar()
        if result == 0:
            db.session.execute(db.text("ALTER TABLE accused ADD COLUMN pincode VARCHAR(10) NULL"))

        result2 = db.session.execute(
            db.text(
                """
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'accused'
                  AND COLUMN_NAME = 'aadhaar_no'
                """
            )
        ).scalar()
        if result2 == 0:
            db.session.execute(db.text("ALTER TABLE accused ADD COLUMN aadhaar_no VARCHAR(20) NULL"))

        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('SELECT 1 FROM judge_decision LIMIT 1'))
    except Exception:
        try:
            db.create_all()
        except Exception:
            pass

    ensure_master_auth_seed()

    try:
        col = db.session.execute(
            db.text(
                """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'judge_decision'
                  AND COLUMN_NAME = 'total_fine'
                """
            )
        ).scalar()
        if col == 0:
            db.session.execute(db.text("ALTER TABLE judge_decision ADD COLUMN total_fine VARCHAR(50) NULL"))

        col2 = db.session.execute(
            db.text(
                """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'judge_decision'
                  AND COLUMN_NAME = 'imprisonment'
                """
            )
        ).scalar()
        if col2 == 0:
            db.session.execute(db.text("ALTER TABLE judge_decision ADD COLUMN imprisonment VARCHAR(50) NULL"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('SELECT 1 FROM meeting_link LIMIT 1'))
    except Exception:
        try:
            db.create_all()
        except Exception:
            pass
