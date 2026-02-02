import os
import re
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from decorators import admin_required
from extensions import csrf, db
from models import (
    Accused,
    Admin,
    ComplaintDescription,
    SectionPunishment,
    SuperAdminMessage,
)



def register_public_routes(app):
    @app.route('/')
    @app.route('/home')
    def home():
        return render_template('home.html')

    @app.route('/base')
    def base():
        return render_template('base.html')

    @app.route('/department', methods=['GET', 'POST'])
    def department():
        csrf_token = generate_csrf()
        selected_case_type = None

        case_types_rows = db.session.query(Accused.case_type).filter(Accused.case_type.isnot(None)).distinct().all()
        case_types = [row[0] for row in case_types_rows]

        if request.method == 'POST':
            selected_case_type = request.form.get('case_type') or None

        if selected_case_type:
            filtered_accused = Accused.query.filter_by(case_type=selected_case_type).all()
        else:
            filtered_accused = Accused.query.all()

        return render_template(
            'add_department.html',
            case_types=case_types,
            filtered_accused=filtered_accused,
            selected_case_type=selected_case_type or '',
            csrf_token=csrf_token,
        )

    @app.route('/user_details')
    def user_details():
        accused_list = Accused.query.all()
        return render_template('user_details.html', accused=accused_list)

    @app.route('/add_user')
    def add_user():
        return render_template('add_user.html', csrf_token=generate_csrf())

    @app.route('/super_add_user')
    def super_add_user():
        return render_template('super_add_user.html', csrf_token=generate_csrf())

    @app.route('/add_accused', methods=['POST'])
    def add_accused():
        username = request.form.get('username')
        relative_name = request.form.get('relative_name')
        relation = request.form.get('relation')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        nationality = request.form.get('nationality')
        occupation = request.form.get('occupation')
        education = request.form.get('education')

        height = request.form.get('height')
        weight = request.form.get('weight')
        waist_size = request.form.get('waist_size')
        foot_size = request.form.get('foot_size')

        special_mark_yes_no = request.form.get('special_mark_yes_no')
        special_mark_cut = request.form.get('special_mark_cut') if special_mark_yes_no == 'Yes' else None

        skin_color = request.form.get('skin_color')

        tattoo_yes_no = request.form.get('tattoo_yes_no')
        tattoo = request.form.get('tattoo') if tattoo_yes_no == 'Yes' else None

        accessories_yes_no = request.form.get('accessories_yes_no')
        accessories_wearing = request.form.get('accessories_wearing') if accessories_yes_no == 'Yes' else None

        blood_group = request.form.get('blood_group')

        medical_report_pdf = None
        proof_evidence_pdf = None
        accused_photo = None

        if 'medical_report_pdf' in request.files:
            medical_file = request.files['medical_report_pdf']
            if medical_file and medical_file.filename:
                filename = secure_filename(f"medical_report_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                medical_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                medical_report_pdf = filename

        if 'proof_evidence_pdf' in request.files:
            evidence_file = request.files['proof_evidence_pdf']
            if evidence_file and evidence_file.filename:
                filename = secure_filename(f"proof_evidence_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                evidence_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                proof_evidence_pdf = filename

        if 'accused_photo' in request.files:
            photo_file = request.files['accused_photo']
            if photo_file and photo_file.filename:
                filename = secure_filename(f"accused_photo_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                accused_photo = filename

        special_key_point = request.form.get('special_key_point')

        disability_yes_no = request.form.get('disability_yes_no')
        disability = request.form.get('disability') if disability_yes_no == 'Yes' else None

        permanent_address = request.form.get('permanent_address')
        temporary_address = request.form.get('temporary_address') or None
        pincode = request.form.get('pincode') or None
        mobile = request.form.get('mobile')
        email_id = request.form.get('email_id')
        aadhaar_no = request.form.get('aadhaar_no') or None

        fir_no = request.form.get('fir_no')
        case_type = request.form.get('case_type')
        ps = request.form.get('ps')
        case_no = request.form.get('case_no')
        sections = request.form.get('sections')
        date_of_arrest = request.form.get('date_of_arrest')
        place_of_arrest = request.form.get('place_of_arrest')
        warrant_arrest = request.form.get('warrant_arrest')
        confession_statement = request.form.get('confession_statement')

        court_forward_date_time = request.form.get('court_forward_date_time')
        remand_custody = request.form.get('remand_custody')
        bail_status = request.form.get('bail_status')
        previous_criminal_record = request.form.get('previous_criminal_record')

        def parse_date(date_str):
            if date_str:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            return None

        def parse_datetime(datetime_str):
            if datetime_str:
                return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
            return None

        dob = parse_date(dob)
        date_of_arrest = parse_date(date_of_arrest)
        court_forward_date_time = parse_datetime(court_forward_date_time)

        new_accused = Accused(
            username=username,
            relative_name=relative_name,
            relation=relation,
            dob=dob,
            gender=gender,
            nationality=nationality,
            occupation=occupation,
            education=education,
            height=height,
            weight=weight,
            waist_size=waist_size,
            foot_size=foot_size,
            special_mark_cut=special_mark_cut,
            skin_color=skin_color,
            tattoo=tattoo,
            accessories_wearing=accessories_wearing,
            blood_group=blood_group,
            medical_report_pdf=medical_report_pdf,
            proof_evidence_pdf=proof_evidence_pdf,
            special_key_point=special_key_point,
            disability=disability,
            accused_photo=accused_photo,
            permanent_address=permanent_address,
            temporary_address=temporary_address,
            pincode=pincode,
            mobile=mobile,
            email_id=email_id,
            aadhaar_no=aadhaar_no,
            fir_no=fir_no,
            case_type=case_type,
            ps=ps,
            case_no=case_no,
            sections=sections,
            date_of_arrest=date_of_arrest,
            place_of_arrest=place_of_arrest,
            warrant_arrest=warrant_arrest,
            confession_statement=confession_statement,
            court_forward_date_time=court_forward_date_time,
            remand_custody=remand_custody,
            bail_status=bail_status,
            previous_criminal_record=previous_criminal_record,
        )

        try:
            db.session.add(new_accused)
            db.session.commit()
            flash('Accused added successfully!', 'success')
            return redirect(url_for('user_details'))
        except Exception as e:
            db.session.rollback()
            if 'Duplicate entry' in str(e) and 'case_no' in str(e):
                flash(f'Error: Case number "{case_no}" already exists. Please use a different case number.', 'error')
            else:
                flash(f'Error adding accused: {str(e)}', 'error')
            return redirect(url_for('add_user'))

    @app.route('/it_team_details')
    def it_team_details():
        team = Admin.query.all()
        return render_template('it_team_details.html', team=team, csrf_token=generate_csrf())

    @app.route('/add_it_team')
    def add_it_team():
        return render_template('add_it_team.html', csrf_token=generate_csrf())

    @app.route('/add_admin', methods=['POST'])
    def add_admin():
        username = request.form['username']
        password = request.form['password']
        mobile_no = request.form['mobile']
        email = request.form['email_id']

        new_admin = Admin(
            username=username,
            password=generate_password_hash(password),
            mobile_no=mobile_no,
            email=email,
        )

        db.session.add(new_admin)
        db.session.commit()

        return redirect(url_for('it_team_details'))

    @app.route('/submit_complain', methods=['GET', 'POST'])
    def submit_complain():
        accused = None
        searched = False

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            dob_str = request.form.get('dob', '').strip()
            aadhaar_no = request.form.get('aadhaar_no', '').strip()

            dob = None
            if dob_str:
                for _fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                    try:
                        dob = datetime.strptime(dob_str, _fmt).date()
                        break
                    except ValueError:
                        continue

            if username and dob and aadhaar_no:
                def normalize_aadhaar(value):
                    return re.sub(r'\D', '', value or '')

                candidates = Accused.query.filter(
                    func.lower(Accused.username) == username.lower(),
                    Accused.dob == dob,
                ).all()
                aadhaar_norm = normalize_aadhaar(aadhaar_no)
                for cand in candidates:
                    if normalize_aadhaar(getattr(cand, 'aadhaar_no', '')) == aadhaar_norm:
                        accused = cand
                        break
            searched = True

        return render_template('add_user_complain.html', accused=accused, searched=searched, csrf_token=generate_csrf())

    @app.route('/submit_search', methods=['GET', 'POST'])
    def submit_search():
        accused = None
        searched = False

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            dob_str = request.form.get('dob', '').strip()
            aadhaar_no = request.form.get('aadhaar_no', '').strip()

            dob = None
            if dob_str:
                for _fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                    try:
                        dob = datetime.strptime(dob_str, _fmt).date()
                        break
                    except ValueError:
                        continue

            if username and dob and aadhaar_no:
                def normalize_aadhaar(value):
                    return re.sub(r'\D', '', value or '')

                candidates = Accused.query.filter(
                    func.lower(Accused.username) == username.lower(),
                    Accused.dob == dob,
                ).all()
                aadhaar_norm = normalize_aadhaar(aadhaar_no)
                for cand in candidates:
                    if normalize_aadhaar(getattr(cand, 'aadhaar_no', '')) == aadhaar_norm:
                        accused = cand
                        break
            searched = True

        return render_template('search_record.html', accused=accused, searched=searched, csrf_token=generate_csrf())

    @app.route('/user_complain')
    def user_complain():
        return render_template('user_complain.html', accused=Accused.query.all())

    @app.route('/add_user_complain')
    def add_user_complain():
        return render_template('add_user_complain.html', csrf_token=generate_csrf())

    @app.route('/search_record')
    def search_record():
        return render_template('search_record.html', csrf_token=generate_csrf())

    @app.route('/add_complaint_description')
    def add_complaint_description():
        super_admin_replies = SuperAdminMessage.query.order_by(SuperAdminMessage.created_at.desc()).all()
        return render_template(
            'add_complaint_description.html',
            csrf_token=generate_csrf(),
            super_admin_replies=super_admin_replies,
        )

    @app.route('/complaints', methods=['GET', 'POST'])
    def complaints():
        if request.method == 'POST':
            complain_type = request.form.get('complain_type')
            description = request.form.get('description')
            case_no = request.form.get('case_no')

            accused = Accused.query.filter_by(case_no=case_no).first()
            if not accused:
                return redirect('/add_complaint_description')

            complaint = ComplaintDescription(
                complain_type=complain_type,
                description=description,
                case_no=case_no,
                status='Active',
            )
            db.session.add(complaint)
            db.session.commit()
            return redirect('/add_complaint_description')

        complaint_rows = ComplaintDescription.query.all()
        complaint_types = ['Crime', 'Women', 'Child', 'Senior Citizen', 'Traffic', 'Theft', 'Civil', 'Mental Harassment']
        return render_template(
            'add_complaint_description.html',
            complaint_descriptions=complaint_rows,
            complaint_types=complaint_types,
            csrf_token=generate_csrf(),
        )

    @app.route('/get_punishment_details', methods=['POST'])
    @csrf.exempt
    def get_punishment_details():
        section_id = request.form.get('section_id', '')
        if not section_id:
            return jsonify({'success': False, 'message': 'No section provided'})

        raw_parts = [part.strip() for part in section_id.split(',') if part and part.strip()]
        if not raw_parts:
            return jsonify({'success': False, 'message': 'No valid sections provided'})

        results_by_id = {}
        for part in raw_parts:
            matches = SectionPunishment.query.filter(
                db.or_(
                    SectionPunishment.article_section.like(f'%{part}%'),
                    SectionPunishment.article_section.like(f'{part},%'),
                    SectionPunishment.article_section.like(f'%, {part}%'),
                    SectionPunishment.article_section.like(f'%,{part}%'),
                    SectionPunishment.article_section == part,
                )
            ).all()
            for match in matches:
                if match.id not in results_by_id:
                    results_by_id[match.id] = match

        if not results_by_id:
            return jsonify({'success': False, 'message': 'No punishment details found for provided sections'})

        items = []
        for match in results_by_id.values():
            items.append(
                {
                    'id': match.id,
                    'category': match.category,
                    'sections': match.article_section,
                    'offence': match.offense,
                    'minimum_fine': match.minimum_fine,
                    'possible_punishments': match.possible_punishments or '',
                }
            )

        return jsonify({'success': True, 'items': items})

    @app.route('/manage_sections')
    def manage_sections():
        page = request.args.get('page', 1, type=int)
        sections_pagination = SectionPunishment.query.paginate(page=page, per_page=15, error_out=False)
        return render_template(
            'manage_sections.html',
            sections=sections_pagination.items,
            pagination=sections_pagination,
            csrf_token=generate_csrf(),
        )

    @app.route('/add_section', methods=['POST'])
    def add_section():
        article_section = request.form.get('article_section') or request.form.get('sections')
        offense = request.form.get('offense') or request.form.get('offence')
        new_section = SectionPunishment(
            category=request.form.get('category'),
            article_section=article_section,
            offense=offense,
            possible_punishments=request.form.get('possible_punishments'),
            minimum_fine=request.form.get('minimum_fine'),
        )

        db.session.add(new_section)
        db.session.commit()

        return redirect(url_for('manage_sections'))

    @app.route('/populate_sample_data')
    def populate_sample_data():
        sample_data = [
            {
                'category': 'Theft',
                'article_section': '379, 380, 381',
                'offense': 'Theft of movable property belonging to another person',
                'minimum_fine': 'Rs. 1,000 or imprisonment up to 3 years',
            },
            {
                'category': 'Assault',
                'article_section': '323, 324, 325',
                'offense': 'Voluntarily causing hurt to another person',
                'minimum_fine': 'Rs. 1,000 or imprisonment up to 1 year',
            },
            {
                'category': 'Fraud',
                'article_section': '420, 421, 422',
                'offense': 'Cheating and dishonestly inducing delivery of property',
                'minimum_fine': 'Rs. 5,000 or imprisonment up to 7 years',
            },
            {
                'category': 'Domestic Violence',
                'article_section': '498A',
                'offense': 'Husband or relative of husband subjecting woman to cruelty',
                'minimum_fine': 'Rs. 10,000 or imprisonment up to 3 years',
            },
            {
                'category': 'Traffic Violation',
                'article_section': '279, 280, 281',
                'offense': 'Rash driving or riding on a public way',
                'minimum_fine': 'Rs. 1,000 or imprisonment up to 6 months',
            },
        ]

        for data in sample_data:
            existing = SectionPunishment.query.filter_by(article_section=data['article_section']).first()
            if not existing:
                db.session.add(
                    SectionPunishment(
                        category=data['category'],
                        article_section=data['article_section'],
                        offense=data['offense'],
                        minimum_fine=data['minimum_fine'],
                    )
                )

        db.session.commit()
        return redirect(url_for('manage_sections'))

    @app.route('/fetch_report', methods=['GET', 'POST'])
    def fetch_report():
        results = None
        if request.method == 'POST':
            from_date_str = request.form.get('from_date')
            to_date_str = request.form.get('to_date')

            if from_date_str and to_date_str:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

                results = db.session.query(Accused, ComplaintDescription).join(
                    ComplaintDescription, Accused.case_no == ComplaintDescription.case_no
                ).filter(
                    Accused.date_of_arrest >= from_date,
                    Accused.date_of_arrest <= to_date,
                ).all()
        return render_template('fetch_report.html', results=results, csrf_token=generate_csrf())

    @app.route('/user_change_password')
    def user_change_password():
        return render_template('user_change_password.html', admins=Admin.query.all(), csrf_token=generate_csrf())

    @app.route('/admin_password_reset', methods=['GET', 'POST'])
    def admin_password_reset():
        if request.method == 'POST':
            try:
                admin_id = request.form.get('admin_id')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                if not admin_id:
                    flash('Please select an admin.', 'error')
                    return redirect(url_for('user_change_password'))
                if not new_password or not confirm_password:
                    flash('Please fill in all password fields.', 'error')
                    return redirect(url_for('user_change_password'))
                if new_password != confirm_password:
                    flash('Passwords do not match.', 'error')
                    return redirect(url_for('user_change_password'))
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'error')
                    return redirect(url_for('user_change_password'))

                admin = Admin.query.get(admin_id)
                if admin:
                    admin.password = generate_password_hash(new_password)
                    db.session.commit()
                    flash(f'Password updated successfully for {admin.username}!', 'success')
                else:
                    flash('Admin not found!', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating password: {str(e)}', 'error')

            return redirect(url_for('user_change_password'))

        return render_template('user_change_password.html', admins=Admin.query.all(), csrf_token=generate_csrf())

    @app.route('/about-us')
    def about_us():
        return render_template('about_us.html')

    @app.route('/auth-center')
    def auth_center():
        return render_template('auth_center.html')

    @app.route('/contact-us', methods=['GET', 'POST'])
    def contact_us():
        if request.method == 'POST':
            flash('Thank you for your message! We will get back to you within 24 hours.', 'success')
            return redirect(url_for('contact_us'))
        return render_template('contact_us.html', csrf_token=generate_csrf())

    @app.route('/admin-login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            remember = request.form.get('remember')

            admin = Admin.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password, password):
                from flask import session

                session['admin_logged_in'] = True
                session['admin_username'] = admin.username
                session['admin_id'] = admin.id

                if remember:
                    session.permanent = True

                flash('Login successful! Welcome to the admin panel.', 'success')
                return redirect(url_for('admin_dashboard'))
            flash('Invalid username or password. Please try again.', 'error')
        return render_template('admin_login.html', csrf_token=generate_csrf())

    @app.route('/admin-logout')
    def admin_logout():
        from flask import session

        session.clear()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('admin_login'))

    @app.route('/check_case_number', methods=['POST'])
    def check_case_number():
        case_no = request.form.get('case_no', '').strip()
        if not case_no:
            return jsonify({'exists': False, 'message': 'Case number is required'})

        existing_accused = Accused.query.filter_by(case_no=case_no).first()
        if existing_accused:
            return jsonify(
                {
                    'exists': True,
                    'message': f'Case number "{case_no}" already exists for accused: {existing_accused.username}',
                }
            )
        return jsonify({'exists': False, 'message': 'Case number is available'})

    @app.route('/get_case_numbers', methods=['POST'])
    def get_case_numbers():
        case_type = request.form.get('case_type', '').strip()
        if not case_type:
            return jsonify({'success': False, 'message': 'Case type is required'})

        accused_with_case_type = Accused.query.filter_by(case_type=case_type).all()
        case_numbers = [accused.case_no for accused in accused_with_case_type if accused.case_no]

        return jsonify(
            {
                'success': True,
                'case_numbers': case_numbers,
                'message': f'Found {len(case_numbers)} cases of type "{case_type}"',
            }
        )

    @app.route('/contact_super_admin', methods=['POST'])
    def contact_super_admin():
        case_type = request.form.get('case_type', '').strip()
        case_no = request.form.get('case_no', '').strip()
        message = request.form.get('message', '').strip()

        if not case_type or not case_no or not message:
            flash('All fields are required.', 'error')
            return redirect('/add_complaint_description')

        accused = Accused.query.filter_by(case_no=case_no).first()
        if not accused:
            flash('Invalid case number.', 'error')
            return redirect('/add_complaint_description')

        super_admin_message = SuperAdminMessage(
            case_type=case_type,
            case_no=case_no,
            message=message,
            status='Pending',
        )

        try:
            db.session.add(super_admin_message)
            db.session.commit()
            flash('Message sent to Super Admin successfully!', 'success')
        except Exception:
            db.session.rollback()
            flash('Error sending message. Please try again.', 'error')

        return redirect('/add_complaint_description')

    @app.route('/admin-dashboard')
    @admin_required
    def admin_dashboard():
        total_accused = Accused.query.count()
        total_complaints = ComplaintDescription.query.filter_by(status='Active').count()
        total_sections = SectionPunishment.query.count()
        total_admins = Admin.query.count()

        recent_activities = [
            {'date': '2024-01-15', 'description': 'New accused added', 'user': 'Admin', 'status': 'Completed'},
            {'date': '2024-01-15', 'description': 'Complaint updated', 'user': 'Admin', 'status': 'Completed'},
            {'date': '2024-01-14', 'description': 'Section added', 'user': 'Admin', 'status': 'Completed'},
        ]
        notifications = [
            {'title': 'System Update', 'message': 'System will be updated tonight at 2 AM', 'time': '2 hours ago'},
            {'title': 'New Complaint', 'message': 'A new complaint has been filed', 'time': '4 hours ago'},
        ]

        return render_template(
            'admin_dashboard.html',
            total_accused=total_accused,
            total_complaints=total_complaints,
            total_sections=total_sections,
            total_admins=total_admins,
            recent_activities=recent_activities,
            notifications=notifications,
        )

    @app.route('/admin/criminal-records')
    @admin_required
    def admin_criminal_records():
        return render_template('user_complain.html', accused=Accused.query.all())

    @app.route('/criminal_records')
    def criminal_records():
        return render_template('criminal_record.html', accused=Accused.query.all())
