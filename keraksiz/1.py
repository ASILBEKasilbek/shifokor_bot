import aiosqlite
from datetime import datetime, timedelta
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

# .... (old functions remain as before) ....

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
        # allaqachon mavjud
        return False
    except Exception as e:
        logging.error(f"Karta saqlashda xato: {e}")
        raise

async def get_active_cards():
    """
    Cardlarni (faol) olib keladi va decrypt qilib (id, card_number, card_holder, expiry_date) ro'yxatini qaytaradi.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "SELECT id, card_number, card_holder, expiry_date FROM payment_cards WHERE is_active=1"
            )
            rows = await cursor.fetchall()
            decrypted_cards = []
            for row in rows:
                cid = row[0]
                enc_number = row[1]
                holder = row[2]
                expiry = row[3]
                try:
                    number = cipher.decrypt(enc_number.encode()).decode()
                except Exception as e:
                    logging.error(f"Karta deshifrlashda xato (id={cid}): {e}")
                    number = "<decrypt_error>"
                decrypted_cards.append((cid, number, holder, expiry))
            return decrypted_cards
    except Exception as e:
        logging.error(f"Aktiv kartalarni olishda xato: {e}")
        raise

async def get_all_cards():
    """
    Barcha kartalarni (faol va faol emas) qaytaradi: (id, decrypted_number, holder, expiry, is_active)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "SELECT id, card_number, card_holder, expiry_date, is_active FROM payment_cards"
            )
            rows = await cursor.fetchall()
            out = []
            for row in rows:
                cid = row[0]
                enc_number = row[1]
                holder = row[2]
                expiry = row[3]
                active = row[4]
                try:
                    number = cipher.decrypt(enc_number.encode()).decode()
                except Exception as e:
                    logging.error(f"Karta deshifrlashda xato (id={cid}): {e}")
                    number = "<decrypt_error>"
                out.append((cid, number, holder, expiry, active))
            return out
    except Exception as e:
        logging.error(f"Kartalarni olishda xato: {e}")
        raise

async def delete_card(card_id):
    """
    Karta o'chirilishi: is_active=0 qilib belgilaydi (saqlab qo'yadi).
    """
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.cursor()
            await cursor.execute("UPDATE payment_cards SET is_active=0 WHERE id=?", (card_id,))
            await conn.commit()
            return True
    except Exception as e:
        logging.error(f"Karta o'chirishda xato (id={card_id}): {e}")
        raise

# (keyingi funksiyalar: get_stats, get_subscribers, get_subscribers_count, get_pending_payments, ...)
# Ushbu fayl ichida boshqa funktsiyalarni ham avvalgi kabi saqlab qo'ying (ularni men o'zgartirmadim).
