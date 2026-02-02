from datetime import datetime

from sqlalchemy import ForeignKey

from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    mobile_no = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)


class Accused(db.Model):
    __tablename__ = 'accused'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    username = db.Column(db.String(100), nullable=False)
    relative_name = db.Column(db.String(100), nullable=False)
    relation = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    nationality = db.Column(db.String(20), nullable=False)
    occupation = db.Column(db.String(100), nullable=False)
    education = db.Column(db.String(100), nullable=False)

    height = db.Column(db.String(20))
    weight = db.Column(db.String(20))
    waist_size = db.Column(db.String(20))
    foot_size = db.Column(db.String(20))
    special_mark_cut = db.Column(db.Text)
    skin_color = db.Column(db.String(50))
    tattoo = db.Column(db.Text)
    accessories_wearing = db.Column(db.Text)

    blood_group = db.Column(db.String(10))
    medical_report_pdf = db.Column(db.String(255))
    proof_evidence_pdf = db.Column(db.String(255))

    special_key_point = db.Column(db.Text)
    disability = db.Column(db.Text)
    accused_photo = db.Column(db.String(255))
    pincode = db.Column(db.String(10))
    aadhaar_no = db.Column(db.String(20))

    permanent_address = db.Column(db.Text, nullable=False)
    temporary_address = db.Column(db.Text)
    mobile = db.Column(db.String(15), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)

    fir_no = db.Column(db.String(50))
    case_type = db.Column(db.String(50))
    ps = db.Column(db.String(100))
    case_no = db.Column(db.String(50))
    sections = db.Column(db.String(255))
    date_of_arrest = db.Column(db.Date)
    place_of_arrest = db.Column(db.String(150))
    warrant_arrest = db.Column(db.String(10))
    confession_statement = db.Column(db.Text)

    court_forward_date_time = db.Column(db.DateTime)
    remand_custody = db.Column(db.String(50))
    bail_status = db.Column(db.String(100))
    previous_criminal_record = db.Column(db.String(255))


class SectionPunishment(db.Model):
    __tablename__ = 'section_punishment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(100), nullable=False)
    article_section = db.Column(db.String(255), nullable=True)
    offense = db.Column(db.Text, nullable=True)
    possible_punishments = db.Column(db.Text, nullable=True)
    minimum_fine = db.Column(db.String(100), nullable=True)


class ComplaintDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complain_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    case_no = db.Column(db.String(50), db.ForeignKey('accused.case_no'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Active')

    accused = db.relationship('Accused', backref='complaints')


class SuperAdminMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(50), nullable=False)
    case_no = db.Column(db.String(50), db.ForeignKey('accused.case_no'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.now)
    replied_at = db.Column(db.DateTime, nullable=True)

    accused = db.relationship('Accused', backref='super_admin_messages')


class JudgeDecision(db.Model):
    __tablename__ = 'judge_decision'

    id = db.Column(db.Integer, primary_key=True)
    case_no = db.Column(db.String(50), db.ForeignKey('accused.case_no'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    decided_at = db.Column(db.DateTime, default=datetime.now)
    total_fine = db.Column(db.String(50), nullable=True)
    imprisonment = db.Column(db.String(50), nullable=True)


class MeetingLink(db.Model):
    __tablename__ = 'meeting_link'

    id = db.Column(db.Integer, primary_key=True)
    case_no = db.Column(db.String(50), db.ForeignKey('accused.case_no'), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Ongoing')
    created_at = db.Column(db.DateTime, default=datetime.now)
    ended_at = db.Column(db.DateTime, nullable=True)
