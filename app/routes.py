# -*- coding: utf-8 -*-
"""
Модуль: routes.py
Описание: Маршруты API и веб-интерфейса
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app.models import db, User, Return
from app.business_logic import ReturnBusinessLogic

main = Blueprint('main', __name__)
api = Blueprint('api', __name__, url_prefix='/api')


# ==================== ВЕБ-МАРШРУТЫ ====================

@main.route('/')
@login_required
def dashboard():
    """
    Маршрут: dashboard
    Описание: Главная панель управления
    
    Возвращает:
        render_template: Страница dashboard.html
    """
    stats = ReturnBusinessLogic.get_return_statistics()
    recent_returns = Return.query.order_by(
        Return.created_at.desc()
    ).limit(10).all()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         returns=recent_returns)


@main.route('/login', methods=['GET', 'POST'])
def login():
    """
    Маршрут: login
    Описание: Страница входа в систему
    
    Возвращает:
        render_template/redirect: Страница login.html или redirect
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                return render_template('login.html', 
                                     error='Аккаунт заблокирован')
            
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', 
                                 error='Неверное имя пользователя или пароль')
    
    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    """Маршрут: logout - Выход из системы"""
    logout_user()
    return redirect(url_for('main.login'))


@main.route('/returns')
@login_required
def return_list():
    """
    Маршрут: return_list
    Описание: Список всех возвратов
    """
    status_filter = request.args.get('status', '')
    query = Return.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    returns = query.order_by(Return.created_at.desc()).all()
    
    return render_template('return_list.html', 
                         returns=returns, 
                         current_filter=status_filter)


@main.route('/returns/new', methods=['GET', 'POST'])
@login_required
def create_return():
    """
    Маршрут: create_return
    Описание: Создание новой заявки на возврат
    """
    if request.method == 'POST':
        # Получение данных из формы
        return_data = {
            'order_id': request.form.get('order_id'),
            'customer_name': request.form.get('customer_name'),
            'customer_phone': request.form.get('customer_phone'),
            'product_name': request.form.get('product_name'),
            'product_article': request.form.get('product_article'),
            'amount': float(request.form.get('amount')),
            'reason': request.form.get('reason')
        }
        
        # Валидация бизнес-правил
        purchase_date = datetime.strptime(
            request.form.get('purchase_date'), '%Y-%m-%d'
        )
        is_valid, message = ReturnBusinessLogic.validate_return_period(
            purchase_date
        )
        
        if not is_valid:
            return render_template('return_form.html', error=message)
        
        # Создание объекта возврата
        new_return = Return(**return_data)
        new_return.status = Return.STATUS_NEW
        
        # Определение маршрута согласования
        approval_route = ReturnBusinessLogic.determine_approval_route(
            return_data['amount']
        )
        
        db.session.add(new_return)
        db.session.commit()
        
        # TODO: Отправка уведомления ответственному
        
        return redirect(url_for('main.return_detail', id=new_return.id))
    
    return render_template('return_form.html')


@main.route('/returns/<int:id>')
@login_required
def return_detail(id):
    """
    Маршрут: return_detail
    Описание: Детальная информация о возврате
    """
    return_obj = Return.query.get_or_404(id)
    can_approve = current_user.can_approve_return(return_obj.amount)
    
    return render_template('return_detail.html', 
                         return_obj=return_obj,
                         can_approve=can_approve)


# ==================== API МАРШРУТЫ ====================

@api.route('/returns', methods=['GET'])
@login_required
def api_get_returns():
    """
    API: GET /api/returns
    Описание: Получение списка возвратов (JSON)
    """
    returns = Return.query.all()
    return jsonify([r.to_dict() for r in returns])


@api.route('/returns/<int:id>', methods=['GET'])
@login_required
def api_get_return(id):
    """API: GET /api/returns/<id> - Получение возврата по ID"""
    return_obj = Return.query.get_or_404(id)
    return jsonify(return_obj.to_dict())


@api.route('/returns', methods=['POST'])
@login_required
def api_create_return():
    """
    API: POST /api/returns
    Описание: Создание возврата через API
    """
    data = request.get_json()
    
    required_fields = ['order_id', 'customer_name', 'product_name', 
                      'amount', 'reason']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    
    new_return = Return(
        order_id=data['order_id'],
        customer_name=data['customer_name'],
        customer_phone=data.get('customer_phone'),
        product_name=data['product_name'],
        product_article=data.get('product_article'),
        amount=data['amount'],
        reason=data['reason'],
        status=Return.STATUS_NEW
    )
    
    db.session.add(new_return)
    db.session.commit()
    
    return jsonify(new_return.to_dict()), 201


@api.route('/returns/<int:id>/approve', methods=['POST'])
@login_required
def api_approve_return(id):
    """
    API: POST /api/returns/<id>/approve
    Описание: Согласование возврата
    """
    return_obj = Return.query.get_or_404(id)
    
    # Проверка прав
    if not current_user.can_approve_return(return_obj.amount):
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    return_obj.status = Return.STATUS_APPROVED
    return_obj.processed_by = current_user.id
    
    # TODO: Интеграция с 1С для создания возвратной накладной
    # TODO: Интеграция с Bitrix24 для обновления сделки
    
    db.session.commit()
    
    return jsonify({
        'message': 'Возврат согласован',
        'return': return_obj.to_dict()
    })


@api.route('/returns/<int:id>/reject', methods=['POST'])
@login_required
def api_reject_return(id):
    """API: POST /api/returns/<id>/reject - Отклонение возврата"""
    return_obj = Return.query.get_or_404(id)
    
    data = request.get_json()
    rejection_reason = data.get('reason', 'Не указана причина')
    
    return_obj.status = Return.STATUS_REJECTED
    return_obj.processed_by = current_user.id
    return_obj.reason = f"{return_obj.reason}\n[Отклонено: {rejection_reason}]"
    
    db.session.commit()
    
    return jsonify({'message': 'Возврат отклонен'})


@api.route('/statistics', methods=['GET'])
@login_required
def api_statistics():
    """API: GET /api/statistics - Статистика возвратов"""
    stats = ReturnBusinessLogic.get_return_statistics()
    return jsonify(stats)


@api.route('/check-fraud/<phone>', methods=['GET'])
@login_required
def api_check_fraud(phone):
    """API: GET /api/check-fraud/<phone> - Проверка на мошенничество"""
    indicators = ReturnBusinessLogic.check_fraud_indicators(phone)
    return jsonify(indicators)