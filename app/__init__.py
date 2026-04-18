import os

from flask import Flask
from flask_login import LoginManager

from config import DevelopmentConfig, config_by_name
from app.models import User, db


login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message = "Пожалуйста, войдите в систему"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(config_name=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    selected_config = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(selected_config, DevelopmentConfig))

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes import api, main

    app.register_blueprint(main)
    app.register_blueprint(api)

    return app
