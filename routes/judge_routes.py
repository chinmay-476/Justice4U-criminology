import hmac
import os
import secrets
import re
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func

from decorators import judge_required
from extensions import csrf, db
from models import Accused, JudgeDecision, MeetingLink
from video_signaling import extract_room_id_from_link, notify_signaling_terminate
from security import (
    check_login_block,
    clear_login_failures,
    is_valid_case_no,
    record_login_failure,
)


def _is_internal_video_link(link):
    return bool(link and '/video-call/' in str(link))


def _case_key(case_no):
    return (case_no or '').strip().lower()


def _safe_case_fragment(case_no):
    cleaned = re.sub(r'[^A-Za-z0-9]+', '-', (case_no or '').strip()).strip('-')
    return cleaned[:48] or 'case'


def _new_room_link_for_case(case_no):
    room_suffix = secrets.token_urlsafe(6).replace('-', '').replace('_', '')
    room_id = f"{_safe_case_fragment(case_no)}-{room_suffix}"
    return url_for('video_call_room', room_id=room_id)


def _ensure_internal_meeting_link(meeting):
    if not meeting or _is_internal_video_link(meeting.link):
        return meeting
    meeting.link = _new_room_link_for_case(meeting.case_no)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return meeting


def _find_latest_ongoing_meeting(case_no):
    key = _case_key(case_no)
    if not key:
        return None
    meeting = (
        MeetingLink.query.filter(MeetingLink.status == 'Ongoing')
        .filter(func.lower(func.trim(MeetingLink.case_no)) == key)
        .order_by(MeetingLink.created_at.desc(), MeetingLink.id.desc())
        .first()
    )
    return meeting


def _normalize_meetings_for_case_map(meetings):
    normalized = {}
    touched = False
    for meeting in meetings:
        if not _is_internal_video_link(meeting.link):
            meeting.link = _new_room_link_for_case(meeting.case_no)
            touched = True
        case_key = _case_key(meeting.case_no)
        if case_key and case_key not in normalized:
            normalized[case_key] = meeting
    if touched:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return normalized


def _judge_api_auth_error():
    return jsonify({'success': False, 'message': 'Judge session expired. Please log in again.'}), 401


def _notify_room_terminated(link, reason='meeting_ended'):
    room_id = extract_room_id_from_link(link)
    if not room_id:
        return False
    return notify_signaling_terminate(current_app.config, room_id, reason=reason)



def register_judge_routes(app):
    @app.route('/get_meeting_link', methods=['POST'])
    @csrf.exempt
    def get_meeting_link():
        if not session.get('judge_logged_in'):
            return _judge_api_auth_error()

        case_no = request.form.get('case_no', '').strip()
        if not is_valid_case_no(case_no):
            return jsonify({'success': False, 'message': 'Case number is required'})

        meeting = _find_latest_ongoing_meeting(case_no)
        if not meeting:
            return jsonify({'success': True, 'link': None})
        meeting = _ensure_internal_meeting_link(meeting)
        return jsonify({'success': True, 'link': meeting.link})

    @app.route('/judge-login', methods=['GET', 'POST'])
    def judge_login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember')

            blocked, remaining_seconds = check_login_block('judge')
            if blocked:
                flash(f'Too many failed attempts. Try again in {remaining_seconds} seconds.', 'error')
                return render_template('judge_login.html', csrf_token=generate_csrf())

            expected_username = os.getenv('JUDGE_USERNAME', 'judge')
            expected_password = os.getenv('JUDGE_PASSWORD', 'judge123')

            if hmac.compare_digest((username or '').strip(), expected_username) and hmac.compare_digest((password or '').strip(), expected_password):
                session.clear()
                session['judge_logged_in'] = True
                session['judge_username'] = 'Judge'
                if remember:
                    session.permanent = True
                clear_login_failures('judge')
                flash('Judge login successful.', 'success')
                return redirect(url_for('judge_dashboard'))
            record_login_failure('judge')
            flash('Invalid judge credentials.', 'error')
        return render_template('judge_login.html', csrf_token=generate_csrf())

    @app.route('/judge-logout')
    def judge_logout():
        session.clear()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('judge_login'))

    @app.route('/judge-dashboard')
    @judge_required
    def judge_dashboard():
        accused_list = Accused.query.order_by(Accused.case_no.asc()).all()

        ongoing_meetings = MeetingLink.query.filter_by(status='Ongoing').order_by(MeetingLink.created_at.desc()).all()
        meeting_links_by_case = _normalize_meetings_for_case_map(ongoing_meetings)

        return render_template(
            'judge_accused.html',
            accused=accused_list,
            ongoing_meetings=ongoing_meetings,
            meeting_links_by_case=meeting_links_by_case,
            csrf_token=generate_csrf(),
        )

    @app.route('/judge/pending')
    @judge_required
    def judge_pending():
        pending = (
            db.session.query(Accused)
            .join(JudgeDecision, JudgeDecision.case_no == Accused.case_no)
            .filter(JudgeDecision.status == 'Pending')
            .all()
        )

        ongoing = MeetingLink.query.filter_by(status='Ongoing').all()
        meeting_links_by_case = _normalize_meetings_for_case_map(ongoing)

        return render_template(
            'judge_pending.html',
            accused=pending,
            meeting_links_by_case=meeting_links_by_case,
            csrf_token=generate_csrf(),
        )

    @app.route('/judge/solved')
    @judge_required
    def judge_solved():
        solved = (
            db.session.query(Accused, JudgeDecision)
            .join(JudgeDecision, JudgeDecision.case_no == Accused.case_no)
            .filter(JudgeDecision.status == 'Solved')
            .all()
        )
        return render_template('judge_solved.html', solved=solved, csrf_token=generate_csrf())

    @app.route('/judge/mark-solved', methods=['POST'])
    @judge_required
    def judge_mark_solved():
        case_no = request.form.get('case_no', '').strip()
        if not case_no:
            flash('Case number is required.', 'error')
            return redirect(url_for('judge_pending'))

        decision = JudgeDecision.query.filter_by(case_no=case_no).first()
        if not decision:
            decision = JudgeDecision(case_no=case_no, status='Solved', decided_at=datetime.now())
            db.session.add(decision)
        else:
            decision.status = 'Solved'
            decision.decided_at = datetime.now()

        try:
            db.session.commit()
            flash('Case marked as solved.', 'success')
        except Exception:
            db.session.rollback()
            flash('Failed to mark as solved.', 'error')

        return redirect(url_for('judge_pending'))

    @app.route('/judge/submit-decision', methods=['POST'])
    @judge_required
    def judge_submit_decision():
        case_no = request.form.get('case_no', '').strip()
        decision = request.form.get('decision', '').strip()
        total_fine = request.form.get('total_fine', '').strip()
        imprisonment = request.form.get('imprisonment', '').strip()

        if not case_no or decision not in ['Pending', 'Solved']:
            flash('Invalid submission.', 'error')
            return redirect(url_for('judge_dashboard'))

        accused = Accused.query.filter_by(case_no=case_no).first()
        if not accused:
            flash('Case not found.', 'error')
            return redirect(url_for('judge_dashboard'))

        existing = JudgeDecision.query.filter_by(case_no=case_no).first()
        if existing:
            existing.status = decision
            existing.decided_at = datetime.now()
            existing.total_fine = total_fine or None
            existing.imprisonment = imprisonment or None
        else:
            db.session.add(
                JudgeDecision(
                    case_no=case_no,
                    status=decision,
                    total_fine=total_fine or None,
                    imprisonment=imprisonment or None,
                )
            )

        try:
            db.session.commit()
            flash('Decision saved successfully.', 'success')
        except Exception:
            db.session.rollback()
            flash('Failed to save decision.', 'error')

        accused_list = Accused.query.order_by(Accused.case_no.asc()).all()

        ongoing_meetings = MeetingLink.query.filter_by(status='Ongoing').order_by(MeetingLink.created_at.desc()).all()
        meeting_links_by_case = _normalize_meetings_for_case_map(ongoing_meetings)

        return render_template(
            'judge_accused.html',
            accused=accused_list,
            ongoing_meetings=ongoing_meetings,
            meeting_links_by_case=meeting_links_by_case,
            csrf_token=generate_csrf(),
        )

    @app.route('/judge/save_meeting_link', methods=['POST'])
    @csrf.exempt
    def judge_save_meeting_link():
        if not session.get('judge_logged_in'):
            return _judge_api_auth_error()

        case_no = request.form.get('case_no', '').strip()
        if not is_valid_case_no(case_no):
            return jsonify({'success': False, 'message': 'Invalid case number'}), 400

        link = _new_room_link_for_case(case_no)

        case_key = _case_key(case_no)
        existing = (
            MeetingLink.query.filter(MeetingLink.status == 'Ongoing')
            .filter(func.lower(func.trim(MeetingLink.case_no)) == case_key)
            .all()
        )
        ended_links = []
        for meeting in existing:
            meeting.status = 'Ended'
            meeting.ended_at = datetime.now()
            ended_links.append(meeting.link)

        try:
            if existing:
                db.session.commit()
        except Exception:
            db.session.rollback()

        for ended_link in ended_links:
            _notify_room_terminated(ended_link, reason='superseded_by_new_meeting')

        new_meeting = MeetingLink(case_no=case_no, link=link, status='Ongoing')
        try:
            db.session.add(new_meeting)
            db.session.commit()
            return jsonify({'success': True, 'link': link})
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Failed to save meeting link'}), 500

    @app.route('/judge/end_meeting/<int:meeting_id>', methods=['POST'])
    @csrf.exempt
    @judge_required
    def judge_end_meeting(meeting_id):
        meeting = MeetingLink.query.get(meeting_id)
        if not meeting or meeting.status != 'Ongoing':
            flash('Meeting not found or already ended.', 'error')
            return redirect(url_for('judge_dashboard'))

        meeting.status = 'Ended'
        meeting.ended_at = datetime.now()
        try:
            db.session.commit()
            flash('Meeting ended successfully.', 'success')
            _notify_room_terminated(meeting.link, reason='ended_by_judge')
        except Exception:
            db.session.rollback()
            flash('Failed to end meeting.', 'error')

        return redirect(url_for('judge_dashboard'))
