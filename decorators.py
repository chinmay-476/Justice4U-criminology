from functools import wraps

from flask import flash, redirect, session, url_for


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('Please log in to access the admin panel.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_or_super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in') and not session.get('super_admin_logged_in'):
            flash('Please log in with admin privileges.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('super_admin_logged_in'):
            flash('Please log in as Super Admin to access this area.', 'error')
            return redirect(url_for('super_admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def judge_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('judge_logged_in'):
            flash('Please log in as Judge to access this area.', 'error')
            return redirect(url_for('judge_login'))
        return f(*args, **kwargs)

    return decorated_function
