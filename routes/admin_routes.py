from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import generate_csrf

from decorators import admin_required
from extensions import db
from models import Accused, ComplaintDescription, JudgeDecision, MeetingLink, SectionPunishment, SuperAdminMessage



def register_admin_routes(app):
    @app.route('/admin/accused-details')
    @admin_required
    def admin_accused_details():
        accused_list = Accused.query.all()
        return render_template('user_details.html', accused=accused_list, csrf_token=generate_csrf())

    @app.route('/admin/accused/delete/<int:accused_id>', methods=['POST'])
    @admin_required
    def admin_accused_delete(accused_id):
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

    @app.route('/admin/accused/edit/<int:accused_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_accused_edit(accused_id):
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
                return redirect(url_for('admin_accused_details'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to update accused: {str(e)}', 'error')

        return render_template('admin_edit_user.html', accused=accused, csrf_token=generate_csrf())

    @app.route('/admin/complaint-description')
    @admin_required
    def admin_complaint_description():
        complaints = ComplaintDescription.query.all()
        complaint_types = ['Crime', 'Women', 'Child', 'Senior Citizen', 'Traffic', 'Theft', 'Civil', 'Mental Harassment']
        return render_template(
            'add_complaint_description.html',
            complaint_descriptions=complaints,
            complaint_types=complaint_types,
            csrf_token=generate_csrf(),
        )

    @app.route('/admin/section-management')
    @admin_required
    def admin_section_management():
        page = request.args.get('page', 1, type=int)
        sections_pagination = SectionPunishment.query.paginate(page=page, per_page=15, error_out=False)
        return render_template(
            'manage_sections.html',
            sections=sections_pagination.items,
            pagination=sections_pagination,
            csrf_token=generate_csrf(),
        )
