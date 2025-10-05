import aiosqlite
from datetime import datetime
from cryptography.fernet import Fernet
from decouple import config
import logging

DB_PATH = "bot_database.db"

# Shifrlash kalitini .env fayldan olish
try:
    key = config('ENCRYPTION_KEY').encode()
    cipher = Fernet(key)
except Exception as e:
    logging.error(f"Shifrlash kalitini olishda xato: {e}")
    raise

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def init_db():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            # Foydalanuvchilar jadvali (expiry_date qo'shildi)
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    gender TEXT,
                    subscription_duration TEXT,
                    username TEXT,
                    chat_preference TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    subscription_date DATE,
                    expiry_date DATE,  -- New column for subscription expiry
                    membership_type TEXT DEFAULT 'oddiy'
                )
            ''')
            # Other tables remain unchanged
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_number TEXT UNIQUE,
                    card_holder TEXT,
                    expiry_date TEXT,
                    cvv TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            await cursor.execute('''
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
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT UNIQUE,
                    channel_username TEXT
                )
            ''')
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    duration TEXT UNIQUE,
                    price REAL
                )
            ''')
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON payments(user_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status)")
            await conn.commit()
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasini boshlashda xato: {e}")
        raise

async def update_user_chat_preference(telegram_id, chat_preference):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "UPDATE users SET chat_preference=? WHERE telegram_id=?",
                (chat_preference, telegram_id)
            )
            await conn.commit()
    except Exception as e:
        logging.error(f"Chat sozlamasini yangilashda xato: {e}")
        raise

async def save_payment(user_id, amount, receipt_id):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "INSERT INTO payments (user_id, amount, receipt_id, payment_date) VALUES (?, ?, ?, ?)",
                (user_id, amount, receipt_id, datetime.now().date())
            )
            payment_id = cursor.lastrowid
            await conn.commit()
            return payment_id
    except Exception as e:
        logging.error(f"To'lov saqlashda xato: {e}")
        raise


async def save_card(card_number, card_holder, expiry_date, cvv):
    try:
        encrypted_card = cipher.encrypt(card_number.encode()).decode()
        encrypted_cvv = cipher.encrypt(cvv.encode()).decode()
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "INSERT INTO payment_cards (card_number, card_holder, expiry_date, cvv) VALUES (?, ?, ?, ?)",
                (encrypted_card, card_holder, expiry_date, encrypted_cvv)
            )
            await conn.commit()
            return True
    except aiosqlite.IntegrityError:
        return False
    except Exception as e:
        logging.error(f"Karta saqlashda xato: {e}")
        raise

async def get_active_cards():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "SELECT card_number, card_holder, expiry_date FROM payment_cards WHERE is_active=1"
            )
            cards = await cursor.fetchall()
            decrypted_cards = [(cipher.decrypt(card[0].encode()).decode(), card[1], card[2]) for card in cards]
            return decrypted_cards
    except Exception as e:
        logging.error(f"Aktiv kartalarni olishda xato: {e}")
        raise

async def get_stats():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT COUNT(*) FROM users WHERE is_active=1")
            total_users = (await cursor.fetchone())[0]
            await cursor.execute("SELECT COUNT(*) FROM payments WHERE status='confirmed'")
            total_payments = (await cursor.fetchone())[0]
            await cursor.execute("SELECT SUM(amount) FROM payments WHERE status='confirmed'")
            total_revenue = (await cursor.fetchone())[0] or 0
            await cursor.execute("SELECT COUNT(*) FROM users WHERE membership_type='majburiy'")
            mandatory_members = (await cursor.fetchone())[0]
            return total_users, total_payments, total_revenue, mandatory_members
    except Exception as e:
        logging.error(f"Statistikani olishda xato: {e}")
        raise

async def get_subscribers(page: int = 1, per_page: int = 10):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """
            SELECT telegram_id, subscription_date, membership_type, subscription_duration, username
            FROM users
            WHERE is_active = 1
            ORDER BY subscription_date DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset)
        )
        rows = await cursor.fetchall()
    return rows


async def get_subscribers_count():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT COUNT(*) FROM users WHERE is_active=1")
            return (await cursor.fetchone())[0]
    except Exception as e:
        logging.error(f"Obunachilar sonini olishda xato: {e}")
        raise

async def get_pending_payments(page: int = 1, per_page: int = 10):
    try:
        offset = (page - 1) * per_page
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "SELECT id, user_id, amount, status FROM payments WHERE status='pending' LIMIT ? OFFSET ?",
                (per_page, offset)
            )
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Kutayotgan to'lovlarni olishda xato: {e}")
        raise

async def get_pending_payments_count():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
            return (await cursor.fetchone())[0]
    except Exception as e:
        logging.error(f"Kutayotgan to'lovlar sonini olishda xato: {e}")
        raise

async def update_membership_type(telegram_id, membership_type):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "UPDATE users SET membership_type=? WHERE telegram_id=?",
                (membership_type, telegram_id)
            )
            await conn.commit()
    except Exception as e:
        logging.error(f"A'zolik turini yangilashda xato: {e}")
        raise

async def save_channel(channel_id, channel_username):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "INSERT OR REPLACE INTO channels (channel_id, channel_username) VALUES (?, ?)",
                (channel_id, channel_username)
            )
            await conn.commit()
            return True
    except aiosqlite.IntegrityError:
        return False
    except Exception as e:
        logging.error(f"Kanal saqlashda xato: {e}")
        raise

async def get_channel():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT channel_id, channel_username FROM channels LIMIT 1")
            return await cursor.fetchone()
    except Exception as e:
        logging.error(f"Kanal ma'lumotlarini olishda xato: {e}")
        raise

async def save_subscription_plan(duration, price):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "INSERT OR REPLACE INTO subscription_plans (duration, price) VALUES (?, ?)",
                (duration, price)
            )
            await conn.commit()
            return True
    except aiosqlite.IntegrityError:
        return False
    except Exception as e:
        logging.error(f"Obuna planini saqlashda xato: {e}")
        raise

async def get_subscription_plans():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT duration, price FROM subscription_plans")
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Obuna planlarini olishda xato: {e}")
        raise

async def get_plan_price(duration):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT price FROM subscription_plans WHERE duration=?", (duration,))
            price = await cursor.fetchone()
            return price[0] if price else 0
    except Exception as e:
        logging.error(f"Obuna narxini olishda xato: {e}")
        raise

async def search_subscribers(query):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "SELECT telegram_id, subscription_date, membership_type, subscription_duration, username FROM users WHERE is_active=1 AND (telegram_id LIKE ? OR subscription_duration LIKE ? OR username LIKE ?)",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Obunachilarni qidirishda xato: {e}")
        raise

from datetime import datetime, timedelta

async def save_user(telegram_id, gender, subscription_duration, username=None):
    try:
        # Calculate expiry date based on subscription duration
        duration_mapping = {
            "1 hafta": timedelta(days=7),
            "1 oy": timedelta(days=30),
            "3 oy": timedelta(days=90),
            # Add other durations as needed
        }
        subscription_start = datetime.now().date()
        expiry_date = subscription_start + duration_mapping.get(subscription_duration, timedelta(days=30))

        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                """
                INSERT OR REPLACE INTO users 
                (telegram_id, gender, subscription_duration, username, subscription_date, expiry_date, is_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (telegram_id, gender, subscription_duration, username, subscription_start, expiry_date, 0)
            )
            await conn.commit()
    except Exception as e:
        logging.error(f"Foydalanuvchi saqlashda xato: {e}")
        raise

async def update_payment_status(payment_id, status, user_id, membership_type):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "UPDATE payments SET status=? WHERE id=?",
                (status, payment_id)
            )
            # Activate user and update subscription details
            if status == 'confirmed':
                await cursor.execute(
                    """
                    UPDATE users 
                    SET is_active=?, membership_type=? 
                    WHERE telegram_id=?
                    """,
                    (1, membership_type, user_id)
                )
            await conn.commit()
    except Exception as e:
        logging.error(f"To'lov statusini yangilashda xato: {e}")
        raise

async def check_expired_subscriptions():
    try:
        today = datetime.now().date()
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                """
                SELECT telegram_id, username 
                FROM users 
                WHERE is_active=1 AND expiry_date <= ?
                """,
                (today,)
            )
            expired_users = await cursor.fetchall()
            for user in expired_users:
                telegram_id = user[0]
                await cursor.execute(
                    "UPDATE users SET is_active=0 WHERE telegram_id=?",
                    (telegram_id,)
                )
            await conn.commit()
            return [(user[0], user[1]) for user in expired_users]
    except Exception as e:
        logging.error(f"Obuna muddati tugaganlarni tekshirishda xato: {e}")
        raise


async def get_user_subscription(telegram_id):
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                """
                SELECT subscription_duration, subscription_date, expiry_date, is_active 
                FROM users 
                WHERE telegram_id=?
                """,
                (telegram_id,)
            )
            return await cursor.fetchone()
    except Exception as e:
        logging.error(f"Foydalanuvchi obuna ma'lumotlarini olishda xato: {e}")
        raise