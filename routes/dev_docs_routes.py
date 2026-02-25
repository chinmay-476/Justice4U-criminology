import os

from flask import abort, render_template, session

from decorators import admin_or_super_admin_required
from extensions import db


def _guess_auth_requirement(path):
    if path in ('/admin-login', '/admin-logout', '/super_admin_login', '/super_admin_logout', '/judge-login', '/judge-logout'):
        return 'Public auth entry'
    if path.startswith('/admin'):
        return 'Admin session'
    if path.startswith('/super'):
        return 'Super admin session'
    if path.startswith('/judge'):
        return 'Judge session'
    if path.startswith('/internal/video-call/'):
        return 'Internal token authentication'
    if path.startswith('/api/video-call/'):
        return 'Room participant (active room)'
    return 'Public or mixed'


def _collect_api_inventory(app):
    rows = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        methods = sorted(method for method in rule.methods if method not in {'HEAD', 'OPTIONS'})
        if not methods:
            continue
        rows.append(
            {
                'path': rule.rule,
                'methods': ', '.join(methods),
                'auth': _guess_auth_requirement(rule.rule),
                'endpoint': rule.endpoint,
            }
        )
    return rows


def _collect_schema_snapshot():
    schema = {}
    for table_name, table in sorted(db.Model.metadata.tables.items(), key=lambda item: item[0]):
        schema[table_name] = [column.name for column in table.columns]
    return schema


def _collect_frontend_assets(app):
    template_dir = os.path.join(app.root_path, 'templates')
    static_dir = os.path.join(app.root_path, 'static')
    templates = sorted([name for name in os.listdir(template_dir) if name.endswith('.html')]) if os.path.isdir(template_dir) else []
    static_roots = sorted(os.listdir(static_dir)) if os.path.isdir(static_dir) else []
    return templates, static_roots


def register_dev_docs_routes(app):
    @app.route('/admin/dev-guide')
    @admin_or_super_admin_required
    def admin_dev_guide():
        if not app.config.get('ENABLE_DEV_DOCS', False):
            abort(404)

        base_template = 'super_admin_base.html' if session.get('super_admin_logged_in') else 'admin_base.html'
        api_inventory = _collect_api_inventory(app)
        db_schema = _collect_schema_snapshot()
        templates, static_roots = _collect_frontend_assets(app)

        backend_modules = [
            {'file': 'app.py', 'purpose': 'App bootstrap, extension init, route registration, security headers'},
            {'file': 'config.py', 'purpose': 'Environment-driven configuration and ENABLE_DEV_DOCS gate'},
            {'file': 'db_init.py', 'purpose': 'Startup schema checks and master auth seeding'},
            {'file': 'models.py', 'purpose': 'SQLAlchemy table definitions'},
            {'file': 'video_signaling.py', 'purpose': 'Internal signaling integration helpers for room termination'},
            {'file': 'routes/public_routes.py', 'purpose': 'Public/admin auth endpoints and core CRUD routes'},
            {'file': 'routes/super_admin_routes.py', 'purpose': 'Super-admin workflows and governance routes'},
            {'file': 'routes/judge_routes.py', 'purpose': 'Judge decisioning and meeting controls'},
            {'file': 'routes/video_call_routes.py', 'purpose': 'Video call room + signaling + chat/image relay'},
            {'file': 'realtime_signaling/src/server.js', 'purpose': 'Node.js Socket.IO signaling service with Redis room state'},
            {'file': 'security.py', 'purpose': 'Validation helpers and login-throttle support'},
        ]

        realtime_notes = [
            'WebRTC media path now supports STUN plus optional TURN from environment.',
            'Primary signaling uses Socket.IO/WebSocket via Node.js service (`/ws/socket.io`).',
            'Fallback signaling remains available via HTTP polling (join/events/signal/leave) when mode is hybrid.',
            'Supported signal types: offer, answer, candidate, hangup, chat_text, chat_image.',
            'Realtime state is designed for Redis-backed rooms/participants in the signaling service.',
        ]

        video_validation_status = {
            'date': 'February 25, 2026',
            'automated': 'API smoke flow passed for polling endpoints; websocket service includes validation helpers and room termination contract.',
            'limits': [
                'Browser-level cross-network E2E still required before production cutover.',
                'TURN credentials must be configured for strict NAT/firewall environments.',
            ],
            'manual_checklist': [
                'Two-browser run: websocket primary mode + hybrid fallback behavior.',
                'Cross-network run: Wi-Fi vs mobile hotspot with TURN enabled.',
                'Judge end-meeting action terminates active websocket room for all participants.',
            ],
        }

        runbook = [
            'pip install -r requirements.txt',
            'python app.py',
            'cd realtime_signaling && npm install && npm run start',
            'python -m unittest tests/test_security_utils.py',
            'python -m unittest tests/test_auth_dev_docs_video_call.py',
            'cd realtime_signaling && npm test',
        ]

        backlog = [
            {
                'priority': 'P0',
                'title': 'Security and reliability',
                'items': [
                    'Harden endpoint authorization boundaries and reduce CSRF exemptions.',
                    'Video call production hardening with TURN + abuse/rate controls.',
                    'Session lifecycle controls for long-lived admin/super-admin sessions.',
                ],
            },
            {
                'priority': 'P1',
                'title': 'Paperwork elimination core',
                'items': [
                    'E-filing wizard with mandatory documents checklist.',
                    'Structured digital forms for FIR/complaint/case packets.',
                    'Role-based task queues for investigation to closure.',
                ],
            },
            {
                'priority': 'P2',
                'title': 'Automation and intelligence',
                'items': [
                    'OCR extraction from uploaded records.',
                    'Auto-drafting templates for orders/notices/summaries.',
                    'Hearing schedule reminders and SLA timeline tracking.',
                ],
            },
            {
                'priority': 'P3',
                'title': 'Audit and interoperability',
                'items': [
                    'Tamper-evident audit trail using document hashing.',
                    'Digital signature workflow.',
                    'Import/export + external system adapters.',
                ],
            },
        ]

        return render_template(
            'admin_dev_guide.html',
            base_template=base_template,
            backend_modules=backend_modules,
            template_files=templates,
            static_roots=static_roots,
            db_schema=db_schema,
            api_inventory=api_inventory,
            realtime_notes=realtime_notes,
            video_validation_status=video_validation_status,
            runbook=runbook,
            backlog=backlog,
        )
