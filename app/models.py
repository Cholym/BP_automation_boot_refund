# -*- coding: utf-8 -*-
"""
Модуль: models.py
Назначение: Модели данных для системы автоматизации возвратов.
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import json
from datetime import datetime, date
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    Класс: User
    Назначение: Модель пользователя системы (продавец, менеджер и др.).

    Атрибуты:
        id (int): Уникальный идентификатор пользователя.
        username (str): Имя пользователя (логин).
        email (str): Электронная почта.
        password_hash (str): Хэш пароля.
        role (str): Роль пользователя ('seller', 'senior_seller', 'manager', 'admin').
        created_at (datetime): Дата создания записи.
        is_active (bool): Статус активности пользователя.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='seller')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    returns = db.relationship('Return', backref='processor', lazy=True)

    def set_password(self, password):
        """
        Функция: set_password
        Назначение: Установка хэша пароля.
        Параметры:
            password (str): Пароль в открытом виде.
        Возвращает:
            None
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Функция: check_password
        Назначение: Проверка пароля.
        Параметры:
            password (str): Пароль для проверки.
        Возвращает:
            bool: True, если пароль верный, иначе False.
        """
        return check_password_hash(self.password_hash, password)

    def can_approve_return(self, _amount=None):
        """
        Функция: can_approve_return
        Назначение: Проверка права на согласование внутренней заявки (менеджер).
        Параметры:
            _amount: Не используется; оставлен для совместимости вызовов.
        Возвращает:
            bool: True, если пользователь может согласовать возврат.
        """
        return self.role in ('manager', 'admin')

    def can_process_return(self, return_obj):
        """
        Функция: can_process_return
        Назначение: Право одобрить/отклонить заявку с учётом статуса и источника.
        Параметры:
            return_obj (Return): Заявка на возврат.
        Возвращает:
            bool: True, если доступны действия согласования.
        """
        if return_obj.status == Return.STATUS_AWAITING_SELLER:
            return self.role in ('seller', 'manager', 'admin')
        if return_obj.status == Return.STATUS_NEW and return_obj.source == Return.SOURCE_STAFF:
            return self.role in ('manager', 'admin')
        return False

    def to_dict(self):
        """
        Функция: to_dict
        Назначение: Сериализация объекта в словарь.
        Возвращает:
            dict: Поля пользователя для JSON.
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }


class Order(db.Model):
    """
    Класс: Order
    Назначение: Заказ для истории продавца и быстрого оформления возврата.
    """

    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(120))
    product_name = db.Column(db.String(200), nullable=False)
    product_article = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    order_status = db.Column(db.String(30), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Return(db.Model):
    """
    Класс: Return
    Назначение: Модель заявки на возврат товара.
    """

    __tablename__ = 'returns'

    SOURCE_STAFF = 'staff'
    SOURCE_CUSTOMER = 'customer'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(120))
    product_name = db.Column(db.String(200), nullable=False)
    product_article = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    one_c_sync = db.Column(db.Boolean, default=False)
    bitrix_deal_id = db.Column(db.String(50))

    source = db.Column(db.String(20), default=SOURCE_STAFF, nullable=False)
    reason_code = db.Column(db.String(50))
    reason_other = db.Column(db.Text)
    product_disposition = db.Column(db.String(30))
    attachment_paths = db.Column(db.Text)
    rejection_reason_code = db.Column(db.String(50))
    return_instructions = db.Column(db.Text)
    purchase_date = db.Column(db.Date)

    STATUS_NEW = 'new'
    STATUS_CHECKING = 'checking'
    STATUS_AWAITING_SELLER = 'awaiting_seller'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'

    def get_attachment_list(self):
        """
        Функция: get_attachment_list
        Назначение: Список имён файлов вложений (JSON в attachment_paths).
        Возвращает:
            list[str]: Имена файлов.
        """
        if not self.attachment_paths:
            return []
        try:
            data = json.loads(self.attachment_paths)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self):
        """
        Функция: to_dict
        Назначение: Сериализация объекта в словарь.
        Возвращает:
            dict: Поля заявки для JSON.
        """
        return {
            'id': self.id,
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'product_name': self.product_name,
            'product_article': self.product_article,
            'amount': self.amount,
            'reason': self.reason,
            'status': self.status,
            'source': self.source,
            'reason_code': self.reason_code,
            'product_disposition': self.product_disposition,
            'attachments': self.get_attachment_list(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'processed_by': self.processed_by,
            'one_c_sync': self.one_c_sync,
            'rejection_reason_code': self.rejection_reason_code,
            'return_instructions': self.return_instructions,
        }

    def get_status_label(self):
        """
        Функция: get_status_label
        Назначение: Получение отображаемого названия статуса.
        Возвращает:
            str: Название статуса на русском языке.
        """
        labels = {
            'new': 'Новая заявка',
            'checking': 'На проверке',
            'awaiting_seller': 'Ожидает решения продавца',
            'approved': 'Одобрен',
            'rejected': 'Отклонён',
            'completed': 'Завершено',
        }
        return labels.get(self.status, self.status)


class Product(db.Model):
    """
    Класс: Product
    Назначение: Модель товара (кэш из 1С).

    Атрибуты:
        id (int): Уникальный идентификатор.
        article (str): Артикул.
        name (str): Наименование.
        price (float): Цена.
        quantity (int): Количество.
        category (str): Категория.
        last_sync (datetime): Время последней синхронизации.
    """

    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100))
    last_sync = db.Column(db.DateTime)

    def to_dict(self):
        """
        Функция: to_dict
        Назначение: Сериализация объекта в словарь.
        Возвращает:
            dict: Поля товара для JSON.
        """
        return {
            'id': self.id,
            'article': self.article,
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category
        }


class AuditLog(db.Model):
    """
    Класс: AuditLog
    Назначение: Журнал действий пользователей и системы.
    """

    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Notification(db.Model):
    """
    Класс: Notification
    Назначение: Уведомления клиенту/сотрудникам (лог канала; без реальной почты в учебном проекте).
    """

    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id'), nullable=True)
    audience = db.Column(db.String(20), nullable=False)
    recipient = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
