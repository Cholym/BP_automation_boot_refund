# BP_automation_boot_refund

Учебный проект: автоматизация возвратов обуви (веб‑интерфейс на Flask).

## Последовательный запуск

1. **Перейти в каталог проекта**

   ```bash
   cd /путь/к/BP_automation_boot_refund
   ```

2. **Создать и активировать виртуальное окружение** (рекомендуется)

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   В Windows (cmd): `.\.venv\Scripts\activate`

3. **Установить зависимости**

   ```bash
   pip install -r requirements.txt
   ```

4. **Инициализировать базу данных** (один раз после клонирования или при пустой БД)

   ```bash
   python app/database/init_db.py
   ```

   Создаётся файл SQLite `app.db` в корне проекта и тестовые пользователи.

5. **Запустить приложение**

   ```bash
   python run.py
   ```

6. **Открыть в браузере**

   Адрес по умолчанию: [http://127.0.0.1:5000](http://127.0.0.1:5000)

   Страница входа: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)

### Тестовые учётные записи (после `init_db.py`)

| Логин   | Пароль    | Роль          |
|---------|-----------|---------------|
| admin   | admin123  | администратор |
| seller  | seller123 | продавец      |
| manager | manager123| менеджер      |

## Дополнительно

- **Порт:** `PORT=8080 python run.py`
- **Режим отладки** (автоперезагрузка при изменении кода): `FLASK_DEBUG=1 python run.py`
- **Окружение:** `FLASK_ENV=production` — конфигурация production из `config.py`
- **Секретный ключ и БД:** переменные `SECRET_KEY` и `DATABASE_URL` (см. `config.py`)
