# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from user_handlers import setup_user_handlers
from admin_handlers import setup_admin_handlers
from dotenv import load_dotenv
import os
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

async def main():
    # Handlerlarni ro'yxatdan o'tkazish
    setup_user_handlers(dp, bot, ADMIN_ID)
    setup_admin_handlers(dp, bot, ADMIN_ID)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())