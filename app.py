import os

from flask import Flask

from config import Config
from db_init import run_startup_schema_checks
from extensions import csrf, db
from routes import register_all_routes



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        run_startup_schema_checks()

    register_all_routes(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Content-Security-Policy', "default-src 'self' 'unsafe-inline' data: https:;")
        return response

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
