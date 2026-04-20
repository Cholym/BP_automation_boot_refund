# -*- coding: utf-8 -*-
"""
Модуль: routes.py
Назначение: Маршруты веб-интерфейса и REST API.
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import json
import os
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    current_app,
    send_from_directory,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import or_

from app.models import db, User, Return, Order, Notification, AuditLog
from app.business_logic import ReturnBusinessLogic
from app.catalogs import RETURN_REASONS, REJECTION_REASONS, label_choices
from app import workflow_service

main = Blueprint("main", __name__)
api = Blueprint("api", __name__, url_prefix="/api")
public = Blueprint("public", __name__)


def _allowed_attachment(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def _save_return_attachments(file_storage_list):
    """
    Функция: _save_return_attachments
    Назначение: Сохранение вложений заявки на диск.
    Возвращает:
        list[str]: Имена сохранённых файлов.
    """
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    saved = []
    for f in file_storage_list:
        if not f or not f.filename:
            continue
        if not _allowed_attachment(f.filename):
            continue
        ext = f.filename.rsplit(".", 1)[1].lower()
        name = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(folder, name)
        f.save(path)
        saved.append(name)
    return saved


def _compose_reason_text(reason_code, reason_other):
    """
    Функция: _compose_reason_text
    Назначение: Текст причины из справочника и поля «Другое».
    """
    label = label_choices(RETURN_REASONS, reason_code) or reason_code or ""
    other = (reason_other or "").strip()
    if reason_code == "other" and other:
        return f"{label}: {other}"
    if other:
        return f"{label}. Дополнительно: {other}"
    return label or "Не указана"


# ==================== ПУБЛИЧНАЯ ФОРМА КЛИЕНТА ====================


@public.route("/public/returns/new", methods=["GET", "POST"])
def customer_return():
    """
    Функция: customer_return
    Назначение: Подача клиентской заявки на возврат (без авторизации).
    Маршрут: GET, POST /public/returns/new
    Возвращает:
        str | Response: HTML или перенаправление.
    """
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        reason_code = request.form.get("reason_code") or "other"
        reason_other = request.form.get("reason_other", "")
        files = request.files.getlist("photos")

        attachments = _save_return_attachments(files)
        if amount > ReturnBusinessLogic.AUTO_APPROVE_MAX_AMOUNT and len(attachments) < 1:
            return render_template(
                "customer_return_form.html",
                error="Для суммы свыше 500 ₽ необходимо приложить хотя бы одно фото "
                "(товар, упаковка или чек).",
                reasons=RETURN_REASONS,
            )

        purchase_raw = request.form.get("purchase_date")
        purchase_date = None
        if purchase_raw:
            try:
                purchase_date = datetime.strptime(purchase_raw, "%Y-%m-%d").date()
            except ValueError:
                purchase_date = None

        reason_text = _compose_reason_text(reason_code, reason_other)
        new_return = Return(
            order_id=request.form.get("order_id") or "CLIENT-UNKNOWN",
            customer_name=request.form.get("customer_name", "").strip(),
            customer_phone=request.form.get("customer_phone", "").strip() or None,
            customer_email=request.form.get("customer_email", "").strip() or None,
            product_name=request.form.get("product_name", "").strip(),
            product_article=request.form.get("product_article", "").strip() or None,
            amount=amount,
            reason=reason_text,
            status=Return.STATUS_AWAITING_SELLER,
            source=Return.SOURCE_CUSTOMER,
            reason_code=reason_code,
            reason_other=reason_other or None,
            purchase_date=purchase_date,
            attachment_paths=json.dumps(attachments) if attachments else None,
        )
        db.session.add(new_return)
        db.session.flush()
        workflow_service.log_audit(
            None,
            "return_created",
            "return",
            new_return.id,
            {"source": Return.SOURCE_CUSTOMER, "status": new_return.status},
        )
        workflow_service.on_customer_return_submitted(new_return)
        db.session.commit()
        return render_template(
            "customer_return_success.html",
            return_id=new_return.id,
        )

    return render_template("customer_return_form.html", reasons=RETURN_REASONS)


# ==================== ВЕБ-МАРШРУТЫ ====================


@main.route("/")
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

    return render_template(
        "dashboard.html", stats=stats, returns=recent_returns
    )


@main.route("/login", methods=["GET", "POST"])
def login():
    """
    Функция: login
    Назначение: Страница входа в систему.
    Маршрут: GET, POST /login
    Возвращает:
        str | Response: HTML login.html или перенаправление на панель.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                return render_template(
                    "login.html", error="Аккаунт заблокирован"
                )

            login_user(user)
            return redirect(url_for("main.dashboard"))
        else:
            return render_template(
                "login.html",
                error="Неверное имя пользователя или пароль",
            )

    return render_template("login.html")


@main.route("/logout")
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
    return redirect(url_for("main.login"))


@main.route("/audit-log")
@login_required
def audit_log_list():
    """
    Функция: audit_log_list
    Назначение: Просмотр журнала аудита действий.
    Маршрут: GET /audit-log
    Возвращает:
        str: HTML.
    """
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("audit_log_list.html", rows=rows)


@main.route("/notifications")
@login_required
def notification_list():
    """
    Функция: notification_list
    Назначение: Лента уведомлений (записи канала учебного стенда).
    Маршрут: GET /notifications
    Возвращает:
        str: HTML.
    """
    items = (
        Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    )
    return render_template("notification_list.html", items=items)


@main.route("/orders")
@login_required
def order_list():
    """
    Функция: order_list
    Назначение: История заказов с поиском и фильтром.
    Маршрут: GET /orders
    Возвращает:
        str: HTML order_list.html.
    """
    q = (request.args.get("q") or "").strip()
    status_filter = request.args.get("status", "").strip()
    query = Order.query
    if status_filter:
        query = query.filter_by(order_status=status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Order.order_id.ilike(like),
                Order.customer_name.ilike(like),
                Order.customer_phone.ilike(like),
                Order.product_name.ilike(like),
            )
        )
    orders = query.order_by(Order.purchase_date.desc()).all()
    return render_template(
        "order_list.html",
        orders=orders,
        q=q,
        current_status=status_filter,
    )


@main.route("/returns")
@login_required
def return_list():
    """
    Функция: return_list
    Назначение: Список всех возвратов.
    Маршрут: GET /returns
    Возвращает:
        str: HTML-страница return_list.html.
    """
    status_filter = request.args.get("status", "")
    query = Return.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    returns = query.order_by(Return.created_at.desc()).all()

    return render_template(
        "return_list.html",
        returns=returns,
        current_filter=status_filter,
    )


@main.route("/returns/new", methods=["GET", "POST"])
@login_required
def create_return():
    """
    Функция: create_return
    Назначение: Создание заявки продавцом (данные можно подтянуть из заказа).
    Маршрут: GET, POST /returns/new
    Возвращает:
        str | Response: HTML return_form.html или перенаправление.
    """
    prefilled = None
    order_id_q = request.args.get("order_id")
    if request.method == "GET" and order_id_q:
        ord_row = Order.query.filter_by(order_id=order_id_q).first()
        if ord_row:
            prefilled = ord_row

    if request.method == "POST":
        reason_code = request.form.get("reason_code")
        reason_other = request.form.get("reason_other", "")
        disposition = request.form.get("product_disposition")

        return_data = {
            "order_id": request.form.get("order_id"),
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "customer_email": request.form.get("customer_email") or None,
            "product_name": request.form.get("product_name"),
            "product_article": request.form.get("product_article"),
            "amount": float(request.form.get("amount")),
            "reason": _compose_reason_text(reason_code, reason_other),
            "source": Return.SOURCE_STAFF,
            "reason_code": reason_code,
            "reason_other": reason_other or None,
            "product_disposition": disposition or None,
        }

        purchase_date = datetime.strptime(
            request.form.get("purchase_date"), "%Y-%m-%d"
        ).date()
        is_valid, message = ReturnBusinessLogic.validate_return_period(
            datetime.combine(purchase_date, datetime.min.time())
        )

        if not is_valid:
            return render_template(
                "return_form.html",
                error=message,
                reasons=RETURN_REASONS,
                prefilled=prefilled,
            )

        return_data["purchase_date"] = purchase_date
        new_return = Return(**return_data)
        new_return.status = Return.STATUS_NEW

        db.session.add(new_return)
        db.session.flush()
        workflow_service.log_audit(
            current_user.id,
            "return_created",
            "return",
            new_return.id,
            {"source": Return.SOURCE_STAFF, "status": new_return.status},
        )

        if ReturnBusinessLogic.is_staff_auto_approve(new_return):
            workflow_service.on_return_approved(new_return, current_user.id)
        db.session.commit()

        return redirect(url_for("main.return_detail", id=new_return.id))

    return render_template(
        "return_form.html",
        reasons=RETURN_REASONS,
        prefilled=prefilled,
    )


@main.route("/returns/<int:id>")
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
    can_process = current_user.can_process_return(return_obj)

    return render_template(
        "return_detail.html",
        return_obj=return_obj,
        can_process=can_process,
        rejection_reasons=REJECTION_REASONS,
        return_reason_label=label_choices(RETURN_REASONS, return_obj.reason_code),
    )


@main.route("/uploads/returns/<path:filename>")
@login_required
def serve_return_upload(filename):
    """
    Функция: serve_return_upload
    Назначение: Выдача вложений заявки (только для авторизованных).
    Маршрут: GET /uploads/returns/<filename>
    Возвращает:
        Response: Файл.
    """
    safe = secure_filename(filename)
    if safe != filename:
        return "Некорректное имя файла", 400
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


# ==================== API МАРШРУТЫ ====================


@api.route("/returns", methods=["GET"])
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


@api.route("/returns/<int:id>", methods=["GET"])
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


@api.route("/returns", methods=["POST"])
@login_required
def api_create_return():
    """
    Функция: api_create_return
    Назначение: Создание возврата через API (сотрудник).
    Маршрут: POST /api/returns
    Возвращает:
        Response: JSON созданного возврата (код 201).
    """
    data = request.get_json()

    required_fields = [
        "order_id",
        "customer_name",
        "product_name",
        "amount",
        "reason",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    new_return = Return(
        order_id=data["order_id"],
        customer_name=data["customer_name"],
        customer_phone=data.get("customer_phone"),
        customer_email=data.get("customer_email"),
        product_name=data["product_name"],
        product_article=data.get("product_article"),
        amount=data["amount"],
        reason=data["reason"],
        status=Return.STATUS_NEW,
        source=Return.SOURCE_STAFF,
        reason_code=data.get("reason_code"),
        product_disposition=data.get("product_disposition"),
    )
    db.session.add(new_return)
    db.session.flush()
    workflow_service.log_audit(
        current_user.id,
        "return_created",
        "return",
        new_return.id,
        {"source": Return.SOURCE_STAFF},
    )
    if ReturnBusinessLogic.is_staff_auto_approve(new_return):
        workflow_service.on_return_approved(new_return, current_user.id)
    db.session.commit()

    return jsonify(new_return.to_dict()), 201


@api.route("/returns/<int:id>/approve", methods=["POST"])
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

    if not current_user.can_process_return(return_obj):
        return jsonify({"error": "Недостаточно прав"}), 403
    if return_obj.status not in (
        Return.STATUS_NEW,
        Return.STATUS_AWAITING_SELLER,
    ):
        return jsonify({"error": "Недопустимый статус для согласования"}), 400

    workflow_service.on_return_approved(return_obj, current_user.id)
    db.session.commit()

    return jsonify(
        {
            "message": "Возврат согласован",
            "return": return_obj.to_dict(),
        }
    )


@api.route("/returns/<int:id>/reject", methods=["POST"])
@login_required
def api_reject_return(id):
    """
    Функция: api_reject_return
    Назначение: Отклонение возврата (код из справочника обязателен).
    Маршрут: POST /api/returns/<id>/reject
    Возвращает:
        Response: JSON с результатом отклонения.
    """
    return_obj = Return.query.get_or_404(id)

    if not current_user.can_process_return(return_obj):
        return jsonify({"error": "Недостаточно прав"}), 403
    if return_obj.status not in (
        Return.STATUS_NEW,
        Return.STATUS_AWAITING_SELLER,
    ):
        return jsonify({"error": "Недопустимый статус для отклонения"}), 400

    data = request.get_json() or {}
    rejection_code = data.get("rejection_reason_code")
    if not rejection_code:
        return jsonify(
            {"error": "Укажите rejection_reason_code из справочника"}
        ), 400
    comment = data.get("comment") or data.get("reason")

    try:
        workflow_service.on_return_rejected(
            return_obj, current_user.id, rejection_code, comment
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    db.session.commit()

    return jsonify({"message": "Возврат отклонен"})


@api.route("/statistics", methods=["GET"])
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


@api.route("/check-fraud/<phone>", methods=["GET"])
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
