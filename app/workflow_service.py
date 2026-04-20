# -*- coding: utf-8 -*-
"""
Модуль: workflow_service.py
Назначение: Аудит, уведомления и тексты инструкций при смене статуса возврата.
Автор: Чабанова О.В.
Группа: ПИБД-2206в
Дата: 2026
"""

import json
from flask import current_app

from app.catalogs import REJECTION_REASONS, label_choices
from app.models import db, AuditLog, Notification, Return


def log_audit(user_id, action, entity_type, entity_id, details=None):
    """
    Функция: log_audit
    Назначение: Запись события в журнал аудита.
    """
    row = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
    )
    db.session.add(row)


def _notify(recipient, subject, body, audience, return_id=None):
    note = Notification(
        return_id=return_id,
        audience=audience,
        recipient=recipient,
        subject=subject,
        body=body,
    )
    db.session.add(note)


def build_approval_instructions(return_obj):
    """
    Функция: build_approval_instructions
    Назначение: Сформировать текст инструкции для клиента при одобрении.
    """
    addr = current_app.config.get(
        "RETURN_WAREHOUSE_ADDRESS",
        "Адрес пункта приёма уточняйте у продавца.",
    )
    lines = [
        f"Здравствуйте, {return_obj.customer_name}!",
        "",
        f"Ваша заявка на возврат №{return_obj.id} (заказ {return_obj.order_id}) одобрена.",
        f"Сумма к возврату: {return_obj.amount:.2f} ₽.",
        "",
        "Условия и адрес возврата:",
        f"— {addr}",
        "— Упакуйте товар с сохранением бирок; приложите копию чека при наличии.",
        "— Срок отправки/приноса товара — 7 календарных дней с даты одобрения.",
        "",
        "С уважением, магазин.",
    ]
    return "\n".join(lines)


def on_return_approved(return_obj, actor_user_id):
    """
    Функция: on_return_approved
    Назначение: Одобрение: инструкция, аудит, уведомление клиенту и сотрудникам.
    """
    return_obj.status = Return.STATUS_APPROVED
    return_obj.processed_by = actor_user_id
    text = build_approval_instructions(return_obj)
    return_obj.return_instructions = text

    log_audit(
        actor_user_id,
        "return_approved",
        "return",
        return_obj.id,
        {"amount": return_obj.amount, "source": return_obj.source},
    )

    recipient = return_obj.customer_email or return_obj.customer_phone or "клиент"
    _notify(
        recipient,
        f"Возврат №{return_obj.id} одобрен",
        text,
        "customer",
        return_obj.id,
    )
    _notify(
        "staff:returns",
        f"Заявка №{return_obj.id} переведена в статус «Одобрен»",
        f"Одобрил пользователь id={actor_user_id}. Клиент: {return_obj.customer_name}.",
        "staff",
        return_obj.id,
    )


def on_return_rejected(return_obj, actor_user_id, rejection_code, comment=None):
    """
    Функция: on_return_rejected
    Назначение: Отклонение: код из справочника, аудит, уведомление клиенту.
    """
    label = label_choices(REJECTION_REASONS, rejection_code)
    if not label or label == rejection_code:
        # код должен быть из справочника
        raise ValueError("Некорректный код причины отказа")

    return_obj.status = Return.STATUS_REJECTED
    return_obj.processed_by = actor_user_id
    return_obj.rejection_reason_code = rejection_code
    return_obj.reason = f"{return_obj.reason}\n[Отказ: {label}]"
    extra = f"\nКомментарий: {comment}" if comment else ""
    client_body = (
        f"Здравствуйте, {return_obj.customer_name}.\n\n"
        f"По заявке на возврат №{return_obj.id} принято решение об отказе.\n"
        f"Причина: {label}.{extra}\n\n"
        f"С уважением, магазин."
    )

    log_audit(
        actor_user_id,
        "return_rejected",
        "return",
        return_obj.id,
        {"rejection_reason_code": rejection_code},
    )

    recipient = return_obj.customer_email or return_obj.customer_phone or "клиент"
    _notify(
        recipient,
        f"Возврат №{return_obj.id} отклонён",
        client_body,
        "customer",
        return_obj.id,
    )
    _notify(
        "staff:returns",
        f"Заявка №{return_obj.id} отклонена",
        f"Причина справочника: {label}. Обработал id={actor_user_id}.",
        "staff",
        return_obj.id,
    )


def on_customer_return_submitted(return_obj):
    """
    Функция: on_customer_return_submitted
    Назначение: Уведомление персонала о клиентской заявке (аудит создаётся в маршруте).
    """
    if return_obj.status == Return.STATUS_AWAITING_SELLER:
        _notify(
            "staff:returns",
            f"Новая клиентская заявка №{return_obj.id}",
            f"Ожидает решения продавца. Клиент: {return_obj.customer_name}, "
            f"сумма {return_obj.amount:.2f} ₽.",
            "staff",
            return_obj.id,
        )
