# Criminology Management System

This project is a Flask + MySQL web application for managing criminal case records, complaint descriptions, legal sections, and role-based review workflows (Admin, Super Admin, Judge).

## 1) Project Overview

- Backend: Flask (`app.py`) with SQLAlchemy ORM.
- Database: MySQL (`criminology` schema) via `PyMySQL`.
- Frontend: Jinja templates + AdminLTE/Bootstrap static assets.
- PWA support: `manifest.json`, `service-worker.js`, and `/pwa-test`.
- File uploads: accused photo, medical report PDF, and evidence PDF into `uploads/`.

Main code now lives in:
- `flask_project/criminology/app.py` (entrypoint + app factory)
- `flask_project/criminology/config.py` (configuration)
- `flask_project/criminology/extensions.py` (shared Flask extensions)
- `flask_project/criminology/models.py` (SQLAlchemy models)
- `flask_project/criminology/decorators.py` (auth decorators)
- `flask_project/criminology/routes/` (feature-based route modules)
- `flask_project/criminology/templates/`
- `flask_project/criminology/static/`
- `flask_project/complete_database_setup.sql`

## 2) Functional Modules

- **Accused Management**
  - Create, list, search, edit, delete accused records.
  - Stores personal details, address, and case details.
- **Complaint Management**
  - Add complaint descriptions against a case number.
  - Complaint types include Crime, Women, Child, Theft, etc.
- **Section/Punishment Knowledge Base**
  - Manage legal sections and associated punishments/fines.
  - Fetch details through AJAX endpoint (`/get_punishment_details`).
- **Admin Team Management**
  - Create and remove admin accounts.
  - Admin password reset flow.
- **Judge Workflow**
  - Judge login, review pending cases, mark solved, submit decisions.
  - Save/end case-wise meeting links.
- **Super Admin Workflow**
  - Dashboard stats, judgement view, message/reply center.
  - Can manage IT team records and accused records.
- **Reporting**
  - Date-range report joining accused + complaint data (`/fetch_report`).

## 3) Data Model (Core Tables)

Defined in `app.py` models and `complete_database_setup.sql`:

- `user`: lightweight system users.
- `admin`: admin team credentials and contact.
- `accused`: central case/person record (personal, medical, address, case, court forwarding).
- `section_punishment`: legal sections/articles with offence and punishment details.
- `complaint_description`: complaint type + description linked to `accused.case_no`.
- `super_admin_message`: escalation messages and replies for super admin.
- `judge_decision`: judge status (`Pending`/`Solved`) plus fine/imprisonment.
- `meeting_link`: per-case online meeting links and status (`Ongoing`/`Ended`).

Key relationships:
- `complaint_description.case_no -> accused.case_no`
- `super_admin_message.case_no -> accused.case_no`
- `judge_decision.case_no -> accused.case_no`
- `meeting_link.case_no -> accused.case_no`

## 4) Route Map (High-Level)

Route modules:
- `routes/public_routes.py`
- `routes/admin_routes.py`
- `routes/super_admin_routes.py`
- `routes/judge_routes.py`
- `routes/utility_routes.py`

### Public / General
- `/`, `/home`, `/about-us`, `/contact-us`
- `/add_user`, `/add_accused`, `/user_details`
- `/search_record`, `/submit_search`
- `/submit_complain`, `/add_user_complain`
- `/criminal_records`, `/fetch_report`
- `/manifest.json`, `/service-worker.js`, `/sw.js`, `/pwa-test`

### Admin
- `/admin-login`, `/admin-logout`
- `/admin-dashboard`
- `/admin/accused-details`, `/admin/accused/edit/<id>`, `/admin/accused/delete/<id>`
- `/admin/complaint-description`, `/admin/section-management`
- `/admin/criminal-records`

### Super Admin
- `/super_admin_login`, `/super_admin_logout`
- `/super-admin-dashboard`
- `/super_admin/judgements`
- `/super-admin/messages`, `/super-admin/messages/<id>/reply`
- `/super-admin/save_meeting_link`
- `/super_accused`, `/super_accused/edit/<id>`, `/super_accused/delete/<id>`
- `/super_sections`, `/delete_it_team/<id>`

### Judge
- `/judge-login`, `/judge-logout`
- `/judge-dashboard`, `/judge/pending`, `/judge/solved`
- `/judge/submit-decision`, `/judge/mark-solved`
- `/judge/save_meeting_link`, `/judge/end_meeting/<id>`

### AJAX / Utility Endpoints
- `/get_punishment_details`
- `/get_meeting_link`
- `/check_case_number`
- `/get_case_numbers`
- `/contact_super_admin`

## 5) Setup and Run

1. Create virtual environment and install dependencies:
   - `pip install -r flask_project/criminology/requirements.txt`
2. Prepare MySQL database:
   - Option A: run `flask_project/complete_database_setup.sql`.
   - Option B: let SQLAlchemy auto-create tables on first app start.
3. Update DB connection in `flask_project/criminology/app.py`:
   - `app.config['SQLALCHEMY_DATABASE_URI']`
4. Start app:
   - `python flask_project/criminology/app.py`
5. Open:
   - `http://127.0.0.1:5000`

## 6) Authentication and Roles

- **Admin login**: checks `admin` table (hashed password).
- **Super Admin login**: hard-coded credential path in `app.py`.
- **Judge login**: hard-coded credential path in `app.py`.
- Session keys used:
  - `admin_logged_in`
  - `super_admin_logged_in`
  - `judge_logged_in`

## 7) PWA Notes

- `manifest.json` defines app metadata, icons, shortcuts.
- `service-worker.js` caches static and dynamic routes.
- Background sync code exists but is placeholder (returns empty submissions).

## 8) Analysis Findings (Current Risks / Gaps)

- Secrets and DB credentials are hard-coded in `app.py` (secret key, DB URI).
- Super admin and judge credentials are hard-coded.
- Some write routes are not role-protected, so data operations rely mainly on UI flow.
- Legacy field-name mismatch exists in sample-data route (`sections`/`offence` vs model `article_section`/`offense`).
- Typo risk in super-admin accused edit path (`remand_cuddy`) can break updates.
- Upload validation mainly uses filename extension checks.

## 9) Recommended Next Improvements

- Move secrets/credentials to environment variables (`.env`) and rotate keys.
- Enforce role checks on sensitive create/update/delete routes.
- Normalize schema/migration strategy (Alembic/Flask-Migrate).
- Add server-side validation for all critical fields (case number uniqueness, Aadhaar format, file MIME).
- Add automated tests for auth, CRUD flows, and judge/super-admin decisions.
- Split `app.py` into blueprints (`auth`, `admin`, `judge`, `public`, `api`) for maintainability.
