# -*- coding: utf-8 -*-
"""
Модуль: business_logic.py
Назначение: Бизнес-логика обработки возвратов.
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

from datetime import datetime, timedelta
from app.models import Return, db


class ReturnBusinessLogic:
    """
    Класс: ReturnBusinessLogic
    Назначение: Реализация бизнес-правил обработки возвратов.

    Правила:
        1. Возврат ≤ 500 ₽ от сотрудника согласуется автоматически.
        2. Клиентские заявки не автосогласуются; > 500 ₽ требуют вложений (фото).
        3. Ручное согласование внутренних заявок — менеджер (сумма > 500 ₽).
        4. Решение по клиентским заявкам — продавец / менеджер.
        5. Возврат в течение 14 дней с покупки (для оформления продавцом).
    """

    AUTO_APPROVE_MAX_AMOUNT = 500  # Автовозврат без ручного согласования
    RETURN_PERIOD_DAYS = 14  # Период возврата в днях

    @staticmethod
    def validate_return_period(purchase_date):
        """
        Функция: validate_return_period
        Назначение: Проверка соблюдения срока возврата (14 дней).
        Параметры:
            purchase_date (datetime): Дата покупки.
        Возвращает:
            tuple: Результат проверки (bool) и сообщение (str).
        """
        today = datetime.utcnow().date()
        delta = today - purchase_date.date()

        if delta.days > ReturnBusinessLogic.RETURN_PERIOD_DAYS:
            return False, f"Превышен срок возврата (прошло {delta.days} дней, \
максимум {ReturnBusinessLogic.RETURN_PERIOD_DAYS})"

        return True, "Срок возврата соблюден"

    @staticmethod
    def determine_approval_route(amount):
        """
        Функция: determine_approval_route
        Назначение: Определение маршрута согласования по сумме.
        Параметры:
            amount (float): Сумма возврата.
        Возвращает:
            str: 'auto' или ответственная роль для ручного согласования.
        """
        if amount <= ReturnBusinessLogic.AUTO_APPROVE_MAX_AMOUNT:
            return 'auto'
        return 'manager'

    @staticmethod
    def is_staff_auto_approve(return_obj):
        """
        Функция: is_staff_auto_approve
        Назначение: Проверка, подлежит ли заявка сотрудника автосогласованию (≤ 500 ₽).
        Параметры:
            return_obj (Return): Заявка на возврат.
        Возвращает:
            bool: True, если можно применить автосогласование.
        """
        return (
            return_obj.source == Return.SOURCE_STAFF
            and return_obj.amount <= ReturnBusinessLogic.AUTO_APPROVE_MAX_AMOUNT
        )

    @staticmethod
    def calculate_refund_amount(return_obj, deduction_percent=0):
        """
        Функция: calculate_refund_amount
        Назначение: Расчёт суммы возврата с учётом удержаний.
        Параметры:
            return_obj (Return): Объект возврата.
            deduction_percent (float): Процент удержания (0–100).
        Возвращает:
            float: Сумма к возврату.
        """
        if deduction_percent < 0 or deduction_percent > 100:
            deduction_percent = 0

        deduction = return_obj.amount * (deduction_percent / 100)
        return return_obj.amount - deduction

    @staticmethod
    def get_return_statistics():
        """
        Функция: get_return_statistics
        Назначение: Получение статистики по возвратам.
        Возвращает:
            dict: Статистика возвратов.
        """
        total = Return.query.count()
        new_count = Return.query.filter_by(status=Return.STATUS_NEW).count()
        awaiting = Return.query.filter_by(
            status=Return.STATUS_AWAITING_SELLER).count()
        approved_count = Return.query.filter_by(
            status=Return.STATUS_APPROVED).count()
        rejected_count = Return.query.filter_by(
            status=Return.STATUS_REJECTED).count()

        # Расчет средней суммы возврата
        total_amount = db.session.query(
            db.func.sum(Return.amount)
        ).filter_by(status=Return.STATUS_APPROVED).scalar() or 0

        avg_amount = total_amount / approved_count if approved_count > 0 else 0

        return {
            'total': total,
            'new': new_count,
            'awaiting_seller': awaiting,
            'approved': approved_count,
            'rejected': rejected_count,
            'total_amount': total_amount,
            'avg_amount': avg_amount
        }

    @staticmethod
    def check_fraud_indicators(customer_phone, days_window=30):
        """
        Функция: check_fraud_indicators
        Назначение: Проверка индикаторов мошенничества.
        Параметры:
            customer_phone (str): Телефон клиента.
            days_window (int): Период анализа в днях.
        Возвращает:
            dict: Индикаторы риска.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_window)

        # Количество возвратов от клиента за период
        returns_count = Return.query.filter(
            Return.customer_phone == customer_phone,
            Return.created_at >= cutoff_date
        ).count()

        risk_level = 'low'
        if returns_count >= 5:
            risk_level = 'high'
        elif returns_count >= 3:
            risk_level = 'medium'

        return {
            'returns_count': returns_count,
            'risk_level': risk_level,
            'warning': returns_count >= 3
        }
