# -*- coding: utf-8 -*-
"""
Файл: init_db.py
Описание: Скрипт инициализации базы данных
Автор: Чабанова О.В.
Группа: ПИБД-2206в
"""

import os
import sys

# Добавляем корневую директорию проекта в path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.models import User, db


def init_database():
    """
    Функция: init_database
    Описание: Создание всех таблиц и начальных данных
    """
    app = create_app()

    with app.app_context():
        # Создание всех таблиц
        print("Создание таблиц базы данных...")
        db.create_all()
        print("✓ Таблицы созданы")

        # Проверка наличия администратора
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("Создание тестовых пользователей...")

            # Создание администратора
            admin = User(
                username="admin",
                email="admin@store.ru",
                role="admin",
                is_active=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)

            # Создание продавца
            seller = User(
                username="seller",
                email="seller@store.ru",
                role="seller",
                is_active=True,
            )
            seller.set_password("seller123")
            db.session.add(seller)

            # Создание менеджера
            manager = User(
                username="manager",
                email="manager@store.ru",
                role="manager",
                is_active=True,
            )
            manager.set_password("manager123")
            db.session.add(manager)

            db.session.commit()
            print("✓ Тестовые пользователи созданы")
        else:
            print("ℹ Пользователи уже существуют")

        print("\nБаза данных успешно инициализирована!")
        print("\nТестовые учетные данные:")
        print("  admin / admin123")
        print("  seller / seller123")
        print("  manager / manager123")


if __name__ == "__main__":
    init_database()
