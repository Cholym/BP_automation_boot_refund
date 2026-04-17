# -*- coding: utf-8 -*-
"""
Модуль: one_c.py
Описание: Интеграция с 1С:Розница через REST API
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime


class OneCIntegration:
    """
    Класс: OneCIntegration
    Описание: Клиент для работы с API 1С:Розница
    
    Атрибуты:
        base_url (str): Базовый URL 1С
        username (str): Пользователь 1С
        password (str): Пароль пользователя
    """
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {'Content-Type': 'application/json'}
    
    def check_sale(self, order_id):
        """
        Метод: check_sale
        Описание: Проверка существования чека в 1С
        
        Параметры:
            order_id (str): Номер чека/заказа
        
        Возвращает:
            dict: Информация о продаже или None
        """
        endpoint = f"{self.base_url}/hs/sales/{order_id}"
        
        try:
            response = requests.get(
                endpoint,
                auth=self.auth,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except requests.RequestException as e:
            print(f"Ошибка подключения к 1С: {e}")
            return None
    
    def create_return_document(self, return_data):
        """
        Метод: create_return_document
        Описание: Создание документа возврата в 1С
        
        Параметры:
            return_data (dict): Данные возврата
        
        Возвращает:
            dict: Результат создания документа
        """
        endpoint = f"{self.base_url}/hs/returns"
        
        payload = {
            'order_id': return_data['order_id'],
            'customer_name': return_data['customer_name'],
            'product_article': return_data['product_article'],
            'amount': return_data['amount'],
            'reason': return_data['reason'],
            'date': datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(
                endpoint,
                auth=self.auth,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 201:
                return {
                    'success': True,
                    'document_id': response.json().get('document_id')
                }
            else:
                return {
                    'success': False,
                    'error': response.text
                }
                
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def sync_products(self):
        """
        Метод: sync_products
        Описание: Синхронизация товаров из 1С
        
        Возвращает:
            list: Список товаров
        """
        endpoint = f"{self.base_url}/hs/products"
        
        try:
            response = requests.get(
                endpoint,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except requests.RequestException as e:
            print(f"Ошибка синхронизации товаров: {e}")
            return []