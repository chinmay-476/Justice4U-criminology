from routes.admin_routes import register_admin_routes
from routes.judge_routes import register_judge_routes
from routes.public_routes import register_public_routes
from routes.super_admin_routes import register_super_admin_routes
from routes.utility_routes import register_utility_routes



def register_all_routes(app):
    register_public_routes(app)
    register_admin_routes(app)
    register_super_admin_routes(app)
    register_judge_routes(app)
    register_utility_routes(app)
