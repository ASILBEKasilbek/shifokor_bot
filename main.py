import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from user_handlers import setup_user_handlers
from admin_handlers import setup_admin_handlers
from database import init_db   # ⬅️ qo‘shdik
from dotenv import load_dotenv
from keyboards import get_renew_subscription_keyboard
from datetime import datetime, timedelta
import aiosqlite
from database import DB_PATH, check_expired_subscriptions
load_dotenv()

# Konfiguratsiya
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Logging sozlash
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
async def check_subscriptions_periodically(bot: Bot):
    while True:
        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            # Check for expired subscriptions
            expired_users = await check_expired_subscriptions()
            for telegram_id, username in expired_users:
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"Assalomu alaykum, @{username or 'Foydalanuvchi'}!\n"
                            f"Sizning obunangiz muddati tugadi. Iltimos, yangi obuna sotib oling."
                        ),
                        reply_markup=await get_renew_subscription_keyboard()
                    )
                except Exception as e:
                    logging.error(f"Xabar yuborishda xato (user {telegram_id}): {e}")

            # Check for subscriptions expiring tomorrow
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute(
                    """
                    SELECT telegram_id, username 
                    FROM users 
                    WHERE is_active=1 AND expiry_date = ?
                    """,
                    (tomorrow,)
                )
                expiring_users = await cursor.fetchall()
                for telegram_id, username in expiring_users:
                    try:
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=(
                                f"Assalomu alaykum, @{username or 'Foydalanuvchi'}!\n"
                                f"Sizning obunangiz ertaga ({tomorrow}) tugaydi. Iltimos, obunangizni yangilang."
                            ),
                            reply_markup=await get_renew_subscription_keyboard()
                        )
                    except Exception as e:
                        logging.error(f"Ertaga tugaydigan obuna xabari yuborishda xato (user {telegram_id}): {e}")
        except Exception as e:
            logging.error(f"Obuna tekshirishda xato: {e}")
        # Check every 24 hours
        await asyncio.sleep(24 * 60 * 60)

async def main():
    # Bazani init qilish
    await init_db()   # ⬅️ faqat shu yerda chaqiramiz

    # Handlerlarni ro'yxatdan o'tkazish
    setup_user_handlers(dp, bot, ADMIN_ID)
    setup_admin_handlers(dp, bot, ADMIN_ID)
    asyncio.create_task(check_subscriptions_periodically(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())