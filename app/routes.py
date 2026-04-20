# -*- coding: utf-8 -*-
"""
Модуль: routes.py
Назначение: Маршруты веб-интерфейса и REST API.
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
    Функция: dashboard
    Назначение: Главная панель управления.
    Маршрут: GET /
    Возвращает:
        str: HTML-страница dashboard.html.
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
    Функция: login
    Назначение: Страница входа в систему.
    Маршрут: GET, POST /login
    Возвращает:
        str | Response: HTML login.html или перенаправление на панель.
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
    """
    Функция: logout
    Назначение: Выход из системы.
    Маршрут: GET /logout
    Возвращает:
        Response: Перенаправление на страницу входа.
    """
    logout_user()
    return redirect(url_for('main.login'))


@main.route('/returns')
@login_required
def return_list():
    """
    Функция: return_list
    Назначение: Список всех возвратов.
    Маршрут: GET /returns
    Возвращает:
        str: HTML-страница return_list.html.
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
    Функция: create_return
    Назначение: Создание новой заявки на возврат.
    Маршрут: GET, POST /returns/new
    Возвращает:
        str | Response: HTML return_form.html или перенаправление на карточку.
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

        # Сумма ≤ 500 ₽ — автоматическое согласование без ручного этапа
        ReturnBusinessLogic.try_auto_approve(new_return, current_user.id)

        db.session.add(new_return)
        db.session.commit()

        # TODO: Отправка уведомления ответственному при ручном согласовании

        return redirect(url_for('main.return_detail', id=new_return.id))

    return render_template('return_form.html')


@main.route('/returns/<int:id>')
@login_required
def return_detail(id):
    """
    Функция: return_detail
    Назначение: Детальная информация о возврате.
    Маршрут: GET /returns/<id>
    Возвращает:
        str: HTML-страница return_detail.html.
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
    Функция: api_get_returns
    Назначение: Получение списка возвратов в формате JSON.
    Маршрут: GET /api/returns
    Возвращает:
        Response: JSON-массив возвратов.
    """
    returns = Return.query.all()
    return jsonify([r.to_dict() for r in returns])


@api.route('/returns/<int:id>', methods=['GET'])
@login_required
def api_get_return(id):
    """
    Функция: api_get_return
    Назначение: Получение одного возврата по идентификатору.
    Маршрут: GET /api/returns/<id>
    Возвращает:
        Response: JSON-объект возврата.
    """
    return_obj = Return.query.get_or_404(id)
    return jsonify(return_obj.to_dict())


@api.route('/returns', methods=['POST'])
@login_required
def api_create_return():
    """
    Функция: api_create_return
    Назначение: Создание возврата через API.
    Маршрут: POST /api/returns
    Возвращает:
        Response: JSON созданного возврата (код 201).
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
        status=Return.STATUS_NEW,
    )
    ReturnBusinessLogic.try_auto_approve(new_return, current_user.id)

    db.session.add(new_return)
    db.session.commit()

    return jsonify(new_return.to_dict()), 201


@api.route('/returns/<int:id>/approve', methods=['POST'])
@login_required
def api_approve_return(id):
    """
    Функция: api_approve_return
    Назначение: Согласование возврата.
    Маршрут: POST /api/returns/<id>/approve
    Возвращает:
        Response: JSON с результатом согласования.
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
    """
    Функция: api_reject_return
    Назначение: Отклонение возврата.
    Маршрут: POST /api/returns/<id>/reject
    Возвращает:
        Response: JSON с результатом отклонения.
    """
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
    """
    Функция: api_statistics
    Назначение: Статистика возвратов в формате JSON.
    Маршрут: GET /api/statistics
    Возвращает:
        Response: JSON со статистикой.
    """
    stats = ReturnBusinessLogic.get_return_statistics()
    return jsonify(stats)


@api.route('/check-fraud/<phone>', methods=['GET'])
@login_required
def api_check_fraud(phone):
    """
    Функция: api_check_fraud
    Назначение: Проверка индикаторов мошенничества по телефону.
    Маршрут: GET /api/check-fraud/<phone>
    Возвращает:
        Response: JSON с индикаторами риска.
    """
    indicators = ReturnBusinessLogic.check_fraud_indicators(phone)
    return jsonify(indicators)
