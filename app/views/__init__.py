from flask import Flask

from .admin_dashboard import admin_bp
from .auth import auth_bp
from .static import static_bp
from .test import test_bp
from .user import user_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(static_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(user_bp)
