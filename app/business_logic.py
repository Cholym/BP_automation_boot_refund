# -*- coding: utf-8 -*-
"""
Модуль: business_logic.py
Описание: Бизнес-логика обработки возвратов
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

from datetime import datetime, timedelta
from app.models import Return, db


class ReturnBusinessLogic:
    """
    Класс: ReturnBusinessLogic
    Описание: Реализация бизнес-правил обработки возвратов
    
    Бизнес-правила:
        1. Возврат ≤ 10 000 ₽ может согласовать старший продавец
        2. Возврат > 10 000 ₽ требует согласования менеджера
        3. Возврат возможен в течение 14 дней с момента покупки
        4. Товар должен сохранить товарный вид
    """
    
    MAX_AMOUNT_SENIOR_SELLER = 10000  # Максимальная сумма для старшего продавца
    RETURN_PERIOD_DAYS = 14  # Период возврата в днях
    
    @staticmethod
    def validate_return_period(purchase_date):
        """
        Метод: validate_return_period
        Описание: Проверка соблюдения срока возврата (14 дней)
        
        Параметры:
            purchase_date (datetime): Дата покупки
        
        Возвращает:
            tuple: (bool, str) - результат проверки и сообщение
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
        Метод: determine_approval_route
        Описание: Определение маршрута согласования по сумме
        
        Параметры:
            amount (float): Сумма возврата
        
        Возвращает:
            str: Роль ответственного за согласование
        """
        if amount <= ReturnBusinessLogic.MAX_AMOUNT_SENIOR_SELLER:
            return 'senior_seller'
        else:
            return 'manager'
    
    @staticmethod
    def calculate_refund_amount(return_obj, deduction_percent=0):
        """
        Метод: calculate_refund_amount
        Описание: Расчет суммы возврата с учетом удержаний
        
        Параметры:
            return_obj (Return): Объект возврата
            deduction_percent (float): Процент удержания (0-100)
        
        Возвращает:
            float: Сумма к возврату
        """
        if deduction_percent < 0 or deduction_percent > 100:
            deduction_percent = 0
        
        deduction = return_obj.amount * (deduction_percent / 100)
        return return_obj.amount - deduction
    
    @staticmethod
    def get_return_statistics():
        """
        Метод: get_return_statistics
        Описание: Получение статистики по возвратам
        
        Возвращает:
            dict: Статистика возвратов
        """
        total = Return.query.count()
        new_count = Return.query.filter_by(status=Return.STATUS_NEW).count()
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
            'approved': approved_count,
            'rejected': rejected_count,
            'total_amount': total_amount,
            'avg_amount': avg_amount
        }
    
    @staticmethod
    def check_fraud_indicators(customer_phone, days_window=30):
        """
        Метод: check_fraud_indicators
        Описание: Проверка индикаторов мошенничества
        
        Параметры:
            customer_phone (str): Телефон клиента
            days_window (int): Период анализа в днях
        
        Возвращает:
            dict: Индикаторы риска
        """
        from datetime import datetime, timedelta
        
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