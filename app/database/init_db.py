# -*- coding: utf-8 -*-
"""
Модуль: init_db.py
Назначение: Инициализация базы данных и тестовых пользователей.
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import os
import sys
from datetime import date, timedelta, datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.models import User, db, Order

def _seed_orders():
    """
    Функция: _seed_orders
    Назначение: Демонстрационные заказы для истории продавца.
    Логика дат: 3 заказа — сегодня, 3 — вчера, 3 — позавчера.
    """
    # Защита от дублей при повторном запуске
    if Order.query.count() > 0:
        print("ℹ Заказы уже существуют, пропуск добавления.")
        return

    today = date.today()
    rows = [
        ("CH-001", "Иванов И.И.", "+79991110001", "ivan@mail.ru", "Кроссовки Runner", "ART-1001", 4500.0, today),
        ("CH-002", "Петрова М.С.", "+79991110002", None, "Стельки для обуви Adidas 39", "ART-1002", 1200.0, today),
        ("CH-003", "Сидоров П.А.", "+79991110003", "sid@mail.ru", "Сандали кожанные Puma", "ART-1003", 2800.0, today),
        ("CH-004", "Кузнецова А.В.", "+79991110004", None, "Кроссовки Solomons 42", "ART-1004", 8900.0, today - timedelta(days=1)),
        ("CH-005", "Морозов Д.О.", "+79991110005", "moroz@mail.ru", "Кросовки летние Solomons 37", "ART-1005", 5400.0, today - timedelta(days=1)),
        ("CH-006", "Волкова Е.И.", "+79991110006", None, "Кеды Converse", "ART-1006", 3200.0, today - timedelta(days=1)),
        ("CH-007", "Лебедев М.А.", "+79991110007", "volk@mail.ru", "Рюкзак Nike", "ART-1007", 2100.0, today - timedelta(days=2)),
        ("CH-008", "Соколова В.П.", "+79991110008", None, "Кроссовки зимние Adidas", "ART-1008", 6700.0, today - timedelta(days=2)),
        ("CH-009", "Новиков А.С.", "+79991110009", "zay@mail.ru", "Кроссовки зимние Solomons Black Edition Recycled", "ART-1009", 12500.0, today - timedelta(days=2)),
    ]

    for oid, cname, phone, email, pname, article, amount, pdate in rows:
        db.session.add(
            Order(
                order_id=oid,
                customer_name=cname,
                customer_phone=phone,
                customer_email=email,
                product_name=pname,
                product_article=article,
                amount=amount,
                purchase_date=pdate,
                order_status="completed",
                created_at=datetime.combine(pdate, datetime.min.time()),
            )
        )
    db.session.commit()

def init_database():
    """
    Функция: init_database
    Назначение: Создание таблиц и начальных данных.
    Возвращает:
        None
    """
    app = create_app()

    with app.app_context():
        print("Создание таблиц базы данных...")
        db.create_all()
        print("✓ Таблицы созданы")

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("Создание тестовых пользователей...")

            admin = User(
                username="admin",
                email="admin@store.ru",
                role="admin",
                is_active=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)

            seller = User(
                username="seller",
                email="seller@store.ru",
                role="seller",
                is_active=True,
            )
            seller.set_password("seller123")
            db.session.add(seller)

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

        _seed_orders()

        print("\nБаза данных успешно инициализирована!")
        print("\nТестовые учетные данные:")
        print("  admin / admin123")
        print("  seller / seller123")
        print("  manager / manager123")


if __name__ == "__main__":
    init_database()
