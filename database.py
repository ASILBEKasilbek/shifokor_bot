# database.py
import sqlite3
from datetime import datetime

DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            gender TEXT,
            subscription_duration TEXT,
            chat_preference TEXT,
            is_active BOOLEAN DEFAULT 0,
            subscription_date DATE,
            membership_type TEXT DEFAULT 'oddiy'
        )
    ''')
    # To'lov kartalari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_number TEXT UNIQUE,
            card_holder TEXT,
            expiry_date TEXT,
            cvv TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    # To'lovlar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            receipt_id TEXT,
            status TEXT DEFAULT 'pending',
            payment_date DATE,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    ''')
    # Kanallar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_username TEXT
        )
    ''')
    # Obuna planlari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duration TEXT UNIQUE,
            price REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_user(telegram_id, gender, subscription_duration):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, gender, subscription_duration) VALUES (?, ?, ?)",
                   (telegram_id, gender, subscription_duration))
    conn.commit()
    conn.close()

def update_user_chat_preference(telegram_id, chat_preference):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET chat_preference=? WHERE telegram_id=?", (chat_preference, telegram_id))
    conn.commit()
    conn.close()

def save_payment(user_id, amount, receipt_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, receipt_id, payment_date) VALUES (?, ?, ?, ?)",
                   (user_id, amount, receipt_id, datetime.now().date()))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id

def update_payment_status(payment_id, status, user_id, membership_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status=? WHERE id=?", (status, payment_id))
    cursor.execute("UPDATE users SET is_active=?, subscription_date=?, membership_type=? WHERE telegram_id=?",
                   (1 if status == 'confirmed' else 0, datetime.now().date(), membership_type, user_id))
    conn.commit()
    conn.close()

def save_card(card_number, card_holder, expiry_date, cvv):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO payment_cards (card_number, card_holder, expiry_date, cvv) VALUES (?, ?, ?, ?)",
                       (card_number, card_holder, expiry_date, cvv))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_active_cards():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cards = cursor.execute("SELECT card_number, card_holder, expiry_date FROM payment_cards WHERE is_active=1").fetchall()
    conn.close()
    return cards

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    total_users = cursor.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
    total_payments = cursor.execute("SELECT COUNT(*) FROM payments WHERE status='confirmed'").fetchone()[0]
    total_revenue = cursor.execute("SELECT SUM(amount) FROM payments WHERE status='confirmed'").fetchone()[0] or 0
    mandatory_members = cursor.execute("SELECT COUNT(*) FROM users WHERE membership_type='majburiy'").fetchone()[0]
    conn.close()
    return total_users, total_payments, total_revenue, mandatory_members

def get_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    subscribers = cursor.execute("SELECT telegram_id, subscription_date, membership_type, subscription_duration FROM users WHERE is_active=1").fetchall()
    conn.close()
    return subscribers

def get_pending_payments():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    payments = cursor.execute("SELECT id, user_id, amount, status FROM payments WHERE status='pending'").fetchall()
    conn.close()
    return payments

def update_membership_type(telegram_id, membership_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET membership_type=? WHERE telegram_id=?", (membership_type, telegram_id))
    conn.commit()
    conn.close()

def save_channel(channel_id, channel_username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_username) VALUES (?, ?)",
                       (channel_id, channel_username))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_channel():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    channel = cursor.execute("SELECT channel_id, channel_username FROM channels LIMIT 1").fetchone()
    conn.close()
    return channel

def save_subscription_plan(duration, price):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO subscription_plans (duration, price) VALUES (?, ?)",
                       (duration, price))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_subscription_plans():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    plans = cursor.execute("SELECT duration, price FROM subscription_plans").fetchall()
    conn.close()
    return plans

def get_plan_price(duration):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    price = cursor.execute("SELECT price FROM subscription_plans WHERE duration=?", (duration,)).fetchone()
    conn.close()
    return price[0] if price else 0