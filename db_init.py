from extensions import db


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
