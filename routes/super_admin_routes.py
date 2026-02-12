import hmac
import os
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func

from decorators import super_admin_required
from extensions import csrf, db
from models import (
    Accused,
    Admin,
    ComplaintDescription,
    JudgeDecision,
    MeetingLink,
    SectionPunishment,
    SuperAdminMessage,
    User,
)
from security import (
    check_login_block,
    clear_login_failures,
    is_valid_case_no,
    is_valid_meeting_link,
    record_login_failure,
)



def register_super_admin_routes(app):
    @app.route('/delete_it_team/<int:admin_id>', methods=['POST'])
    @super_admin_required
    def delete_it_team(admin_id):
        try:
            admin = Admin.query.get_or_404(admin_id)
            db.session.delete(admin)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Admin team member deleted successfully!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error deleting admin: {str(e)}'})

    @app.route('/super_admin_login', methods=['GET', 'POST'])
    def super_admin_login():
        if request.method == 'POST':
            username = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            remember = request.form.get('remember')

            blocked, remaining_seconds = check_login_block('super_admin')
            if blocked:
                flash(f'Too many failed attempts. Try again in {remaining_seconds} seconds.', 'error')
                return render_template('super_admin_login.html', csrf_token=generate_csrf())

            expected_username = os.getenv('SUPER_ADMIN_USERNAME', 'admin')
            expected_email = os.getenv('SUPER_ADMIN_EMAIL', 'admin@criminology.com')
            expected_password = os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')

            valid_identity = username in {expected_username, expected_email}
            if valid_identity and hmac.compare_digest(password, expected_password):
                session.clear()
                session['super_admin_logged_in'] = True
                session['super_admin_username'] = 'Super Admin'
                if remember:
                    session.permanent = True
                clear_login_failures('super_admin')
                flash('Super Admin login successful.', 'success')
                return redirect(url_for('super_admin_dashboard'))

            record_login_failure('super_admin')
            flash('Invalid super admin credentials.', 'error')
        return render_template('super_admin_login.html', csrf_token=generate_csrf())

    @app.route('/super_admin_logout')
    def super_admin_logout():
        session.clear()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('super_admin_login'))

    @app.route('/super-admin-dashboard')
    @super_admin_required
    def super_admin_dashboard():
        total_departments = (
            db.session.query(func.count(func.distinct(Accused.case_type)))
            .filter(Accused.case_type.isnot(None), Accused.case_type != '')
            .scalar()
            or 0
        )

        total_admin_teams = Admin.query.count()
        total_users = User.query.count()
        total_messages = SuperAdminMessage.query.filter_by(status='Pending').count()

        return render_template(
            'super_admin_dashboard.html',
            total_departments=total_departments,
            total_admin_teams=total_admin_teams,
            total_users=total_users,
            total_messages=total_messages,
        )

    @app.route('/super_admin/judgements')
    @super_admin_required
    def super_admin_judgements():
        decisions = (
            db.session.query(JudgeDecision, Accused)
            .join(Accused, JudgeDecision.case_no == Accused.case_no)
            .filter(JudgeDecision.status.in_(['Pending', 'Solved']))
            .order_by(JudgeDecision.decided_at.desc())
            .all()
        )
        return render_template('super_admin_judgements.html', decisions=decisions, csrf_token=generate_csrf())

    @app.route('/super-admin/save_meeting_link', methods=['POST'])
    @csrf.exempt
    @super_admin_required
    def super_admin_save_meeting_link():
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

        new_meeting = MeetingLink(case_no=case_no, link=link, status='Ongoing')
        try:
            db.session.add(new_meeting)
            db.session.commit()
            return jsonify({'success': True})
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Failed to save meeting link'}), 500

    @app.route('/super-admin/messages')
    @super_admin_required
    def super_admin_messages():
        messages = SuperAdminMessage.query.order_by(SuperAdminMessage.created_at.desc()).all()
        decisions = JudgeDecision.query.all()
        decisions_by_case = {decision.case_no: decision for decision in decisions}
        return render_template(
            'super_admin_messages.html',
            messages=messages,
            decisions_by_case=decisions_by_case,
            csrf_token=generate_csrf(),
        )

    @app.route('/super-admin/messages/<int:message_id>/reply', methods=['POST'])
    @super_admin_required
    def super_admin_reply(message_id):
        reply_text = request.form.get('reply', '').strip()
        if not reply_text:
            flash('Reply cannot be empty.', 'error')
            return redirect(url_for('super_admin_messages'))

        message = SuperAdminMessage.query.get(message_id)
        if not message:
            flash('Message not found.', 'error')
            return redirect(url_for('super_admin_messages'))

        message.reply = reply_text
        message.status = 'Replied'
        message.replied_at = datetime.now()
        try:
            db.session.commit()
            flash('Reply sent successfully.', 'success')
        except Exception:
            db.session.rollback()
            flash('Failed to send reply. Please try again.', 'error')

        return redirect(url_for('super_admin_messages'))

    @app.route('/super_accused')
    @super_admin_required
    def super_accused():
        accused_list = Accused.query.all()
        return render_template('super_accused.html', accused=accused_list, csrf_token=generate_csrf())

    @app.route('/super_accused/delete/<int:accused_id>', methods=['POST'])
    @super_admin_required
    def super_accused_delete(accused_id):
        try:
            accused = Accused.query.get_or_404(accused_id)
            case_no = accused.case_no

            try:
                db.session.query(JudgeDecision).filter_by(case_no=case_no).delete(synchronize_session=False)
            except Exception:
                pass
            try:
                db.session.query(MeetingLink).filter_by(case_no=case_no).delete(synchronize_session=False)
            except Exception:
                pass
            try:
                db.session.query(ComplaintDescription).filter_by(case_no=case_no).delete(synchronize_session=False)
            except Exception:
                pass
            try:
                db.session.query(SuperAdminMessage).filter_by(case_no=case_no).delete(synchronize_session=False)
            except Exception:
                pass

            db.session.delete(accused)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Accused deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Failed to delete: {str(e)}'})

    @app.route('/super_accused/edit/<int:accused_id>', methods=['GET', 'POST'])
    @super_admin_required
    def super_accused_edit(accused_id):
        accused = Accused.query.get_or_404(accused_id)
        if request.method == 'POST':
            try:
                accused.username = request.form.get('username', accused.username)
                accused.relative_name = request.form.get('relative_name', accused.relative_name)
                accused.relation = request.form.get('relation', accused.relation)

                dob_str = request.form.get('dob', '')
                if dob_str:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                        try:
                            accused.dob = datetime.strptime(dob_str, fmt).date()
                            break
                        except ValueError:
                            continue

                accused.gender = request.form.get('gender', accused.gender)
                accused.nationality = request.form.get('nationality', accused.nationality)
                accused.occupation = request.form.get('occupation', accused.occupation)
                accused.education = request.form.get('education', accused.education)

                accused.height = request.form.get('height', accused.height)
                accused.weight = request.form.get('weight', accused.weight)
                accused.waist_size = request.form.get('waist_size', accused.waist_size)
                accused.foot_size = request.form.get('foot_size', accused.foot_size)
                accused.special_mark_cut = request.form.get('special_mark_cut', accused.special_mark_cut)
                accused.skin_color = request.form.get('skin_color', accused.skin_color)
                accused.tattoo = request.form.get('tattoo', accused.tattoo)
                accused.accessories_wearing = request.form.get('accessories_wearing', accused.accessories_wearing)
                accused.blood_group = request.form.get('blood_group', accused.blood_group)
                accused.special_key_point = request.form.get('special_key_point', accused.special_key_point)
                accused.disability = request.form.get('disability', accused.disability)

                accused.permanent_address = request.form.get('permanent_address', accused.permanent_address)
                accused.temporary_address = request.form.get('temporary_address', accused.temporary_address)
                accused.pincode = request.form.get('pincode', accused.pincode)
                accused.mobile = request.form.get('mobile', accused.mobile)
                accused.email_id = request.form.get('email_id', accused.email_id)
                accused.aadhaar_no = request.form.get('aadhaar_no', accused.aadhaar_no)

                accused.fir_no = request.form.get('fir_no', accused.fir_no)
                accused.case_type = request.form.get('case_type', accused.case_type)
                accused.ps = request.form.get('ps', accused.ps)
                accused.case_no = request.form.get('case_no', accused.case_no)
                accused.sections = request.form.get('sections', accused.sections)

                doa_str = request.form.get('date_of_arrest', '')
                if doa_str:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                        try:
                            accused.date_of_arrest = datetime.strptime(doa_str, fmt).date()
                            break
                        except ValueError:
                            continue

                accused.place_of_arrest = request.form.get('place_of_arrest', accused.place_of_arrest)
                accused.warrant_arrest = request.form.get('warrant_arrest', accused.warrant_arrest)
                accused.confession_statement = request.form.get('confession_statement', accused.confession_statement)

                cdt_str = request.form.get('court_forward_date_time', '')
                if cdt_str:
                    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M'):
                        try:
                            accused.court_forward_date_time = datetime.strptime(cdt_str, fmt)
                            break
                        except ValueError:
                            continue

                accused.remand_custody = request.form.get('remand_custody', accused.remand_custody)
                accused.bail_status = request.form.get('bail_status', accused.bail_status)
                accused.previous_criminal_record = request.form.get(
                    'previous_criminal_record', accused.previous_criminal_record
                )

                db.session.commit()
                flash('Accused details updated successfully', 'success')
                return redirect(url_for('super_accused'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to update accused: {str(e)}', 'error')

        return render_template('super_edit_user.html', accused=accused, csrf_token=generate_csrf())

    @app.route('/super_sections')
    @super_admin_required
    def super_sections():
        page = request.args.get('page', 1, type=int)
        sections_pagination = SectionPunishment.query.paginate(page=page, per_page=15, error_out=False)
        return render_template(
            'super_manage_sections.html',
            sections=sections_pagination.items,
            pagination=sections_pagination,
            csrf_token=generate_csrf(),
        )
