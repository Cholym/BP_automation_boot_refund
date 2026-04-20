# -*- coding: utf-8 -*-
"""
Модуль: __init__.py
Назначение: Фабрика приложения Flask, расширения (БД, вход пользователей).
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

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
    """
    Функция: load_user
    Назначение: Загрузка пользователя по идентификатору сессии.
    Параметры:
        user_id (str): Идентификатор пользователя из cookie.
    Возвращает:
        User | None: Объект пользователя или None.
    """
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(config_name=None):
    """
    Функция: create_app
    Назначение: Создание и настройка экземпляра приложения Flask.
    Параметры:
        config_name (str | None): Имя конфигурации (development, production).
    Возвращает:
        Flask: Настроенное приложение.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    selected_config = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(selected_config, DevelopmentConfig))

    db.init_app(app)
    login_manager.init_app(app)

    upload_dir = app.config.get("UPLOAD_FOLDER")
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)

    from app.routes import api, main, public

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(public)

    return app
