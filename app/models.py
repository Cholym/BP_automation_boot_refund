# -*- coding: utf-8 -*-
"""
Модуль: models.py
Описание: Модели данных для системы автоматизации возвратов
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата создания: 2026
Версия: 1.0
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """
    Класс: User
    Описание: Модель пользователя системы (продавец, старший продавец, менеджер)
    
    Атрибуты:
        id (int): Уникальный идентификатор пользователя
        username (str): Имя пользователя (логин)
        email (str): Электронная почта
        password_hash (str): Хэш пароля
        role (str): Роль пользователя ('seller', 'senior_seller', 'manager')
        created_at (datetime): Дата создания записи
        is_active (bool): Статус активности пользователя
    """
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='seller')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Связь с возвратами (один ко многим)
    returns = db.relationship('Return', backref='processor', lazy=True)
    
    def set_password(self, password):
        """
        Метод: set_password
        Описание: Установка хэша пароля
        
        Параметры:
            password (str): Пароль в открытом виде
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Метод: check_password
        Описание: Проверка пароля
        
        Параметры:
            password (str): Пароль для проверки
        
        Возвращает:
            bool: True если пароль верный, иначе False
        """
        return check_password_hash(self.password_hash, password)
    
    def can_approve_return(self, amount):
        """
        Метод: can_approve_return
        Описание: Проверка права на согласование возврата
        
        Параметры:
            amount (float): Сумма возврата
        
        Возвращает:
            bool: True если пользователь может согласовать, иначе False
        """
        if self.role == 'manager':
            return True
        elif self.role == 'senior_seller' and amount <= 10000:
            return True
        return False
    
    def to_dict(self):
        """Сериализация объекта в словарь"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }


class Return(db.Model):
    """
    Класс: Return
    Описание: Модель заявки на возврат товара
    
    Атрибуты:
        id (int): Уникальный идентификатор возврата
        order_id (str): Номер заказа/чека
        customer_name (str): ФИО клиента
        customer_phone (str): Телефон клиента
        product_name (str): Наименование товара
        product_article (str): Артикул товара
        amount (float): Сумма возврата
        reason (str): Причина возврата
        status (str): Статус заявки
        created_at (datetime): Дата создания
        updated_at (datetime): Дата обновления
        processed_by (int): ID обработавшего пользователя
        one_c_sync (bool): Статус синхронизации с 1С
    """
    
    __tablename__ = 'returns'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    product_name = db.Column(db.String(200), nullable=False)
    product_article = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    one_c_sync = db.Column(db.Boolean, default=False)
    bitrix_deal_id = db.Column(db.String(50))
    
    # Статусы возвратов
    STATUS_NEW = 'new'  # Новая заявка
    STATUS_CHECKING = 'checking'  # На проверке
    STATUS_APPROVED = 'approved'  # Согласовано
    STATUS_REJECTED = 'rejected'  # Отклонено
    STATUS_COMPLETED = 'completed'  # Завершено
    
    def to_dict(self):
        """Сериализация объекта в словарь"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'product_name': self.product_name,
            'product_article': self.product_article,
            'amount': self.amount,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'processed_by': self.processed_by,
            'one_c_sync': self.one_c_sync
        }
    
    def get_status_label(self):
        """
        Метод: get_status_label
        Описание: Получение человеко-читаемого названия статуса
        
        Возвращает:
            str: Название статуса на русском языке
        """
        labels = {
            'new': 'Новая заявка',
            'checking': 'На проверке',
            'approved': 'Согласовано',
            'rejected': 'Отклонено',
            'completed': 'Завершено'
        }
        return labels.get(self.status, self.status)


class Product(db.Model):
    """
    Класс: Product
    Описание: Модель товара (кэш из 1С)
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
        return {
            'id': self.id,
            'article': self.article,
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category
        }