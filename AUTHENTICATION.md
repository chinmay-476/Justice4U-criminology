# Authentication Details - Criminology Project

This document captures the complete authentication setup currently implemented in the project.

## 1) Authentication Types

The system has three role-based login flows:

- **Admin Login** (database-driven)
- **Super Admin Login** (hard-coded credentials)
- **Judge Login** (hard-coded credentials)

Public users can still access public pages without login.

## 2) Credentials (Current)

## 2.1 Admin Credentials

Admin credentials are stored in the `admin` table and verified at login.

- Route: `/admin-login`
- Verification logic file: `routes/public_routes.py`
- Password format: hashed (Werkzeug `generate_password_hash`)

How admin users are created:
- Route: `/add_admin`
- File: `routes/public_routes.py`
- Password is hashed before insert.

Password reset for admin:
- Route: `/admin_password_reset`
- File: `routes/public_routes.py`
- Updates selected admin password with fresh hash.

Note:
- No single hard-coded admin username/password exists in code.
- Credentials depend on database records.

## 2.2 Super Admin Credentials (Hard-Coded)

- Route: `/super_admin_login`
- File: `routes/super_admin_routes.py`
- Accepted username values:
  - `admin`
  - `admin@criminology.com`
- Password:
  - `admin123`

## 2.3 Judge Credentials (Hard-Coded)

- Route: `/judge-login`
- File: `routes/judge_routes.py`
- Username:
  - `judge`
- Password:
  - `judge123`

## 3) Session Keys Used

After successful login:

- Admin:
  - `admin_logged_in = True`
  - `admin_username`
  - `admin_id`
- Super Admin:
  - `super_admin_logged_in = True`
  - `super_admin_username`
- Judge:
  - `judge_logged_in = True`
  - `judge_username`

Logout behavior:
- Admin logout route: `/admin-logout` -> `session.clear()`
- Super admin logout route: `/super_admin_logout` -> `session.clear()`
- Judge logout route: `/judge-logout` -> `session.clear()`

## 4) Access Control Decorators

Defined in: `decorators.py`

- `admin_required`
- `super_admin_required`
- `judge_required`

These decorators guard protected routes and redirect to role-specific login when session key is missing.

## 5) Login/Portal Routes

- **Authentication center (frontend entry page):** `/auth-center`
- Admin login: `/admin-login`
- Super admin login: `/super_admin_login`
- Judge login: `/judge-login`

## 6) Frontend Arrangement Done

To make authentication easier for users:

- Added **Authentication Center** page:
  - `templates/auth_center.html`
  - Gives clean role cards for Admin / Super Admin / Judge.
- Added route:
  - `routes/public_routes.py` -> `/auth-center`
- Updated home page navigation and hero CTA:
  - `templates/home.html`
  - Replaced multiple top login links with one **Access Portals** link.
  - Added quick button to Authentication Center in hero section.

## 7) Security Notes (Important)

Current risks in existing implementation:

- Super Admin and Judge credentials are hard-coded.
- Session protection is basic (no MFA, no lockout/rate-limit in auth flow).
- Credential values are exposed in source code.

Recommended improvement:
- Move all credentials to environment variables and DB-managed users.
- Add rate limiting, login attempt throttling, and password policy.
- Keep this file private if using in production.
