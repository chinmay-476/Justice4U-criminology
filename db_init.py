import os
import re
from datetime import datetime

from extensions import db
from models import Accused, JudgeDecision, MasterAuth, MeetingLink
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


def _is_internal_video_link(link):
    return bool(link and '/video-call/' in str(link))


def _case_key(case_no):
    return (case_no or '').strip().lower()


def _safe_case_fragment(case_no):
    cleaned = re.sub(r'[^A-Za-z0-9]+', '-', (case_no or '').strip()).strip('-')
    return cleaned[:48] or 'case'


def repair_database_records():
    """
    Perform safe, idempotent record repairs for existing data:
    - Normalize legacy third-party meeting links to internal /video-call rooms.
    - Enforce one ongoing meeting per case number.
    - Normalize meeting status/ended_at consistency.
    - Normalize judge decision status values.
    """
    try:
        changed = False
        now = datetime.utcnow()
        valid_case_keys = {
            _case_key(row.case_no)
            for row in Accused.query.with_entities(Accused.case_no).all()
            if _case_key(row.case_no)
        }

        meetings = MeetingLink.query.order_by(MeetingLink.created_at.desc(), MeetingLink.id.desc()).all()
        seen_ongoing = set()

        for meeting in meetings:
            if meeting.case_no and meeting.case_no != meeting.case_no.strip():
                meeting.case_no = meeting.case_no.strip()
                changed = True

            status = (meeting.status or '').strip().title()
            if status not in {'Ongoing', 'Ended'}:
                status = 'Ended' if meeting.ended_at else 'Ongoing'
                meeting.status = status
                changed = True

            case_key = _case_key(meeting.case_no)
            if meeting.status == 'Ongoing':
                if not case_key or (valid_case_keys and case_key not in valid_case_keys):
                    meeting.status = 'Ended'
                    meeting.ended_at = meeting.ended_at or now
                    changed = True
                    continue

                if case_key in seen_ongoing:
                    meeting.status = 'Ended'
                    meeting.ended_at = meeting.ended_at or now
                    changed = True
                    continue

                seen_ongoing.add(case_key)

                if meeting.ended_at is not None:
                    meeting.ended_at = None
                    changed = True

                if not _is_internal_video_link(meeting.link):
                    room_id = f"{_safe_case_fragment(meeting.case_no)}-legacy-{meeting.id}"
                    meeting.link = f"/video-call/{room_id}"
                    changed = True
            else:
                if meeting.ended_at is None:
                    meeting.ended_at = now
                    changed = True

            if meeting.link:
                normalized_link = str(meeting.link).strip()
                if normalized_link != meeting.link:
                    meeting.link = normalized_link
                    changed = True

        decisions = JudgeDecision.query.all()
        for decision in decisions:
            if decision.case_no and decision.case_no != decision.case_no.strip():
                decision.case_no = decision.case_no.strip()
                changed = True
            normalized_status = (decision.status or '').strip().title()
            if normalized_status not in {'Pending', 'Solved'}:
                normalized_status = 'Pending'
            if decision.status != normalized_status:
                decision.status = normalized_status
                changed = True

        if changed:
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

    repair_database_records()
