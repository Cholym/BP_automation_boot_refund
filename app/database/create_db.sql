-- =====================================================
-- Файл: create_db.sql
-- Описание: SQL-скрипт создания базы данных для 
--           системы автоматизации возвратов
-- Автор: Чабанова О.В.
-- Группа: ПИБД-2206в
-- Дата: 2026
-- СУБД: SQLite / PostgreSQL
-- =====================================================

-- Удаление таблиц (если существуют)
DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS audit_log;

-- =====================================================
-- Таблица: users (Пользователи системы)
-- =====================================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'seller',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    
    -- Проверка роли
    CHECK (role IN ('seller', 'senior_seller', 'manager', 'admin'))
);

-- =====================================================
-- Таблица: returns (Возвраты товаров)
-- =====================================================
CREATE TABLE returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20),
    product_name VARCHAR(200) NOT NULL,
    product_article VARCHAR(50),
    amount FLOAT NOT NULL CHECK (amount > 0),
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'new',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_by INTEGER,
    one_c_sync BOOLEAN DEFAULT 0,
    bitrix_deal_id VARCHAR(50),
    
    -- Внешние ключи
    FOREIGN KEY (processed_by) REFERENCES users(id),
    
    -- Проверка статуса
    CHECK (status IN ('new', 'checking', 'approved', 'rejected', 'completed'))
);

-- =====================================================
-- Таблица: products (Товары - кэш из 1С)
-- =====================================================
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    price FLOAT NOT NULL CHECK (price >= 0),
    quantity INTEGER DEFAULT 0 CHECK (quantity >= 0),
    category VARCHAR(100),
    last_sync DATETIME
);

-- =====================================================
-- Таблица: audit_log (Журнал аудита)
-- =====================================================
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =====================================================
-- ИНДЕКСЫ для ускорения поиска
-- =====================================================
CREATE INDEX idx_returns_status ON returns(status);
CREATE INDEX idx_returns_created_at ON returns(created_at DESC);
CREATE INDEX idx_returns_customer_phone ON returns(customer_phone);
CREATE INDEX idx_returns_order_id ON returns(order_id);
CREATE INDEX idx_products_article ON products(article);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- =====================================================
-- НАЧАЛЬНЫЕ ДАННЫЕ (тестовые пользователи)
-- =====================================================

-- Пароли (хэши) для тестовых пользователей:
-- admin: admin123 (хэш нужно сгенерировать через Werkzeug)
-- seller: seller123
-- senior: senior123

INSERT INTO users (username, email, password_hash, role, is_active) VALUES
('admin', 'admin@store.ru', 'pbkdf2:sha256:260000$...', 'admin', 1),
('seller', 'seller@store.ru', 'pbkdf2:sha256:260000$...', 'seller', 1),
('senior', 'senior@store.ru', 'pbkdf2:sha256:260000$...', 'senior_seller', 1),
('manager', 'manager@store.ru', 'pbkdf2:sha256:260000$...', 'manager', 1);

-- Тестовые возвраты
INSERT INTO returns (order_id, customer_name, customer_phone, product_name, 
                     product_article, amount, reason, status) VALUES
('CH-001', 'Иванов Иван Иванович', '+79991234567', 'Кроссовки Nike Air Max', 
 'NK-AM-001', 4500.00, 'Не подошел размер', 'new'),
('CH-002', 'Петрова Мария Сергеевна', '+79997654321', 'Футболка Adidas', 
 'AD-TS-002', 1200.00, 'Брак - пятно', 'approved'),
('CH-003', 'Сидоров Петр Александрович', '+79995551234', 'Шорты Puma', 
 'PM-SH-003', 2800.00, 'Не подошел цвет', 'completed');

-- =====================================================
-- ПРЕДСТАВЛЕНИЯ (Views) для отчетности
-- =====================================================

-- Представление: Статистика возвратов по статусам
CREATE VIEW v_return_statistics AS
SELECT 
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM returns
GROUP BY status;

-- Представление: Топ клиентов по возвратам
CREATE VIEW v_top_customers AS
SELECT 
    customer_name,
    customer_phone,
    COUNT(*) as return_count,
    SUM(amount) as total_amount
FROM returns
GROUP BY customer_name, customer_phone
ORDER BY return_count DESC
LIMIT 10;

-- =====================================================
-- ТРИГГЕРЫ (автоматическое обновление updated_at)
-- =====================================================

CREATE TRIGGER update_returns_timestamp 
AFTER UPDATE ON returns
BEGIN
    UPDATE returns SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- =====================================================
-- КОНЕЦ СКИПТА
-- =====================================================