import hmac
import os
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import generate_csrf

from decorators import judge_required
from extensions import csrf, db
from models import Accused, JudgeDecision, MeetingLink
from security import (
    check_login_block,
    clear_login_failures,
    is_valid_case_no,
    is_valid_meeting_link,
    record_login_failure,
)



def register_judge_routes(app):
    @app.route('/get_meeting_link', methods=['POST'])
    @csrf.exempt
    def get_meeting_link():
        case_no = request.form.get('case_no', '').strip()
        if not is_valid_case_no(case_no):
            return jsonify({'success': False, 'message': 'Case number is required'})

        meeting = (
            MeetingLink.query.filter_by(case_no=case_no, status='Ongoing')
            .order_by(MeetingLink.created_at.desc())
            .first()
        )
        if not meeting:
            return jsonify({'success': True, 'link': None})
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
        decided_case_nos = [decision.case_no for decision in JudgeDecision.query.all()]
        if decided_case_nos:
            accused_list = Accused.query.filter(~Accused.case_no.in_(decided_case_nos)).all()
        else:
            accused_list = Accused.query.all()

        ongoing_meetings = MeetingLink.query.filter_by(status='Ongoing').order_by(MeetingLink.created_at.desc()).all()
        meeting_links_by_case = {meeting.case_no: meeting for meeting in ongoing_meetings}

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
        meeting_links_by_case = {meeting.case_no: meeting for meeting in ongoing}

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

        decided_case_nos = [d.case_no for d in JudgeDecision.query.all()]
        if decided_case_nos:
            accused_list = Accused.query.filter(~Accused.case_no.in_(decided_case_nos)).all()
        else:
            accused_list = Accused.query.all()

        ongoing_meetings = MeetingLink.query.filter_by(status='Ongoing').order_by(MeetingLink.created_at.desc()).all()
        meeting_links_by_case = {meeting.case_no: meeting for meeting in ongoing_meetings}

        return render_template(
            'judge_accused.html',
            accused=accused_list,
            ongoing_meetings=ongoing_meetings,
            meeting_links_by_case=meeting_links_by_case,
            csrf_token=generate_csrf(),
        )

    @app.route('/judge/save_meeting_link', methods=['POST'])
    @csrf.exempt
    @judge_required
    def judge_save_meeting_link():
        case_no = request.form.get('case_no', '').strip()
        link = request.form.get('link', '').strip()
        if not is_valid_case_no(case_no):
            return jsonify({'success': False, 'message': 'Invalid case number'}), 400
        if not is_valid_meeting_link(link):
            return jsonify({'success': False, 'message': 'Invalid meeting link'}), 400

        existing = MeetingLink.query.filter_by(case_no=case_no, status='Ongoing').all()
        for meeting in existing:
            meeting.status = 'Ended'
            meeting.ended_at = datetime.now()

        try:
            if existing:
                db.session.commit()
        except Exception:
            db.session.rollback()

        new_meeting = MeetingLink(case_no=case_no, link=link, status='Ongoing')
        try:
            db.session.add(new_meeting)
            db.session.commit()
            return jsonify({'success': True})
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Failed to save meeting link'}), 500

    @app.route('/judge/end_meeting/<int:meeting_id>', methods=['POST'])
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
        except Exception:
            db.session.rollback()
            flash('Failed to end meeting.', 'error')

        return redirect(url_for('judge_dashboard'))
