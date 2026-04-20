# -*- coding: utf-8 -*-
"""
Модуль: config.py
Назначение: Конфигурация приложения Flask (режимы development/production).
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "app.db")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "returns")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 МБ на запрос
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    # Текст для инструкции клиенту при одобрении (можно переопределить через env)
    RETURN_WAREHOUSE_ADDRESS = os.getenv(
        "RETURN_WAREHOUSE_ADDRESS",
        "г. Москва, ул. Складская, д. 1, пункт приёма возвратов (Пн–Пт 10:00–19:00).",
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}"
    )


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
