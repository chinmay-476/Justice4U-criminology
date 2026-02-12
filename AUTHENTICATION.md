# Authentication Details - Criminology Project

This document reflects the current authentication implementation in the modular codebase.

## Roles and Login Flows

- Admin login (database-backed)
- Super Admin login (environment credential-backed)
- Judge login (environment credential-backed)

Public routes remain accessible without login.

## Credential Sources

### Admin

- Route: `/admin-login`
- File: `routes/public_routes.py`
- Lookup: `Admin` table by email
- Password verification: `check_password_hash`

Admin creation:
- Route: `/add_admin`
- Guard: `@admin_or_super_admin_required`
- Password storage: `generate_password_hash`

Admin password reset:
- Route: `/admin_password_reset`
- Guard: `@admin_or_super_admin_required`
- Rule: non-super-admin can reset only own password

### Super Admin

- Route: `/super_admin_login`
- File: `routes/super_admin_routes.py`
- Credential env vars:
  - `SUPER_ADMIN_USERNAME`
  - `SUPER_ADMIN_EMAIL`
  - `SUPER_ADMIN_PASSWORD`

### Judge

- Route: `/judge-login`
- File: `routes/judge_routes.py`
- Credential env vars:
  - `JUDGE_USERNAME`
  - `JUDGE_PASSWORD`

## Session Keys

On successful login:

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

Logout clears the session:
- `/admin-logout`
- `/super_admin_logout`
- `/judge-logout`

## Access Control Decorators

Defined in `decorators.py`:

- `admin_required`
- `super_admin_required`
- `judge_required`
- `admin_or_super_admin_required`

## Login Throttling

Implemented in `security.py` and applied to all role login routes:

- Sliding window: `10` minutes
- Max attempts before block: `5`
- Block duration: `15` minutes

Helpers:

- `check_login_block(scope)`
- `record_login_failure(scope)`
- `clear_login_failures(scope)`

## Route Protection Coverage (High-Level)

Protected management routes include:

- accused create/list/edit/delete (admin/super-admin controlled as applicable)
- admin account creation/reset
- section management and sample population
- report access
- super-admin dashboard/message/judgement workflows
- judge dashboard and decision workflows

## Production Hardening Checklist

- Set all role credential env vars explicitly (do not rely on defaults).
- Set `SECRET_KEY` explicitly.
- Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Rotate credentials and secret key during deployment.
