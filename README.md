# Criminology Management System

Flask application for criminal case records, complaint tracking, section/punishment lookup, and role-based workflows (Admin, Super Admin, Judge).

## Stack

- Flask + SQLAlchemy + Flask-WTF
- Database via `DATABASE_URL` (default SQLite, MySQL supported)
- Jinja templates + static AdminLTE assets

## Project Layout

- `app.py`: app creation, extension initialization, startup schema checks, security headers
- `config.py`: configuration from environment
- `extensions.py`: `db`, `csrf`
- `models.py`: SQLAlchemy models
- `decorators.py`: access-control decorators
- `security.py`: login throttling and shared input/file/link validators
- `routes/`:
  - `public_routes.py`
  - `admin_routes.py`
  - `super_admin_routes.py`
  - `judge_routes.py`
  - `utility_routes.py`
- `tests/test_security_utils.py`: validation tests for security helpers

## Security and Auth (Current)

- Admin authentication is database-backed (hashed passwords).
- Super Admin and Judge login now use environment variables, not route-hardcoded constants.
- Login throttling is enforced for:
  - Admin login
  - Super Admin login
  - Judge login
- Role guards:
  - `admin_required`
  - `super_admin_required`
  - `judge_required`
  - `admin_or_super_admin_required`
- Sensitive management flows are guarded (admin/super-admin protected), including:
  - admin creation
  - admin password reset
  - section management
  - report access
  - super-admin accused/section pages
- Upload and meeting-link validation is centralized in `security.py`.
- Global response security headers are added in `app.py`.

## Environment Variables

### Core

- `SECRET_KEY`
- `DATABASE_URL` (examples: `sqlite:///criminology.db`, `mysql+pymysql://user:pass@host:3306/dbname`)
- `UPLOAD_FOLDER` (default: `uploads`)
- `SESSION_COOKIE_SECURE` (`true` in production HTTPS)
- `SESSION_COOKIE_SAMESITE` (default: `Lax`)
- `SESSION_LIFETIME_HOURS` (default: `8`)

### Role Credentials

- `SUPER_ADMIN_USERNAME` (default fallback: `admin`)
- `SUPER_ADMIN_EMAIL` (default fallback: `admin@criminology.com`)
- `SUPER_ADMIN_PASSWORD` (default fallback: `admin123`)
- `JUDGE_USERNAME` (default fallback: `judge`)
- `JUDGE_PASSWORD` (default fallback: `judge123`)

## Key Endpoints

### Public

- `/`, `/home`, `/about-us`, `/contact-us`
- `/auth-center`
- `/manifest.json`, `/service-worker.js`, `/sw.js`, `/pwa-test`
- `/health`

### Admin

- `/admin-login`, `/admin-logout`
- `/admin-dashboard`
- `/admin/accused-details`
- `/admin/complaint-description`
- `/admin/section-management`

### Super Admin

- `/super_admin_login`, `/super_admin_logout`
- `/super-admin-dashboard`
- `/super_admin/judgements`
- `/super-admin/messages`

### Judge

- `/judge-login`, `/judge-logout`
- `/judge-dashboard`, `/judge/pending`, `/judge/solved`

## Run

From `flask_project/criminology/`:

```bash
pip install -r requirements.txt
python app.py
```

Default URL: `http://127.0.0.1:5000`

## Tests

From `flask_project/criminology/`:

```bash
python -m unittest tests/test_security_utils.py
```

## Notes

- Defaults for judge/super-admin credentials are still present as fallbacks; set explicit environment values for production.
- CSRF extension is enabled; a small number of JSON endpoints remain `@csrf.exempt` by design.
