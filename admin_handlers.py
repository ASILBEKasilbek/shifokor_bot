from aiogram import Dispatcher, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram import F, BaseMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import *
from keyboards import get_admin_main_keyboard, get_admin_confirm_keyboard, get_membership_keyboard
from states import AdminStates
import logging
from decouple import config
from typing import Callable, Any, Awaitable
import time


# Shifrlash kalitini .env fayldan olish
try:
    from cryptography.fernet import Fernet
    key = config('ENCRYPTION_KEY').encode()
    cipher = Fernet(key)
except Exception as e:
    logging.error(f"Shifrlash kalitini olishda xato: {e}")
    raise

# Logging sozlamalari
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Paginatsiya uchun klaviatura
def get_paginated_keyboard(page: int, total_pages: int, callback_prefix: str = "sub_page") -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="⬅️ Oldingi", callback_data=f"{callback_prefix}_{page-1}")
    builder.button(text=f"{page}/{total_pages}", callback_data="noop")
    if page < total_pages:
        builder.button(text="Keyingi ➡️", callback_data=f"{callback_prefix}_{page+1}")
    builder.button(text="⬅️ Orqaga", callback_data="admin_back")
    builder.adjust(3)
    return builder.as_markup()

def setup_admin_handlers(dp: Dispatcher, bot: Bot):
    # Throttling middleware'ni global qilib qo'yamiz
    # Admin handlers
    @dp.message(Command("admin"))
    async def admin_handler(message: Message):
        logging.debug(f"Admin handler triggered for user_id {message.from_user.id}") # int sifatida
        ADMINS = [5306481482, 7370167126,7818786645,6643594131]
        if message.from_user.id not in ADMINS:
            logging.warning(f"Access denied for user_id {message.from_user.id}")
            await message.answer("Ruxsat yo'q!", show_alert=True)
            return
        await message.answer(
            "Admin panel:",
            reply_markup=await get_admin_main_keyboard()
        )

    @dp.callback_query(F.data.startswith("confirm_") | F.data.startswith("reject_"))
    async def admin_payment_confirmation(callback: CallbackQuery):
        parts = callback.data.split("_")
        action = parts[0]
        payment_id = int(parts[2])
        user_id = int(parts[3])

        status = "confirmed" if action == "confirm" else "rejected"
        membership_type = "oddiy"
        try:
            await update_payment_status(payment_id, status, user_id, membership_type)
            subscription = await get_user_subscription(user_id)
            if subscription:
                duration, sub_date, expiry_date, is_active = subscription
                if status == "confirmed":
                    from aiogram.utils.keyboard import InlineKeyboardBuilder

                    builder = InlineKeyboardBuilder()
                    builder.button(
                        text="👩‍💻 Admin bilan bog'lanish",
                        url="https://t.me/Guliruxsor_Homila_Jinsi"
                    )

                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"✅ Obuna faollashtirildi!\n\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"Obuna ma'lumotlari:\n"
                            f"Tarif: {duration}\n"
                            f"📅 Boshlangan sana: {sub_date} dan\n"
                            f"⏳ Tugash sanasi: {expiry_date} gacha!\n"
                            f"━━━━━━━━━━━━━━━━\n\n"
                            f"🤝 Qo‘llab-quvvatlash bilan bog'lanish uchun pastdagi tugmani bosing va o'zingizga kerakli savolni berib unga javob oling!"
                        ),reply_markup=builder.as_markup() )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text="Afsuski, to'lovingiz rad etildi. Iltimos, qayta urinib ko'ring yoki admin bilan bog'laning."
                    )

                status_text = "Tasdiqlandi" if action == "confirm" else "Rad etildi"
                if callback.message.text:
                    await callback.message.edit_text(f"To'lov {status_text} sifatida yangilandi.")
                elif callback.message.caption:
                    await callback.message.edit_caption(
                        caption=callback.message.caption + f"\n\nTo'lov {status_text} sifatida yangilandi."
                    )
                else:
                    await callback.message.answer(f"To'lov {status_text} sifatida yangilandi.")

        except Exception as e:
            logging.error(f"To'lov tasdiqlashda xato: {e}")
            await callback.message.answer("Xato yuz berdi. Iltimos, qayta urinib ko'ring.")

        await callback.answer()

    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats_handler(callback: CallbackQuery):
        try:
            total_users, total_payments, total_revenue, mandatory_members = await get_stats()
            stats_text = f"""📊 <b>Statistika:</b>
👥 Faol obunachilar: {total_users}
💰 Tasdiqlangan to'lovlar soni: {total_payments}
💵 Umumiy daromad: {total_revenue} so'm
⚡ Majburiy a'zolik: {mandatory_members} ta"""
            await callback.message.edit_text(stats_text)
            await callback.answer()
        except Exception as e:
            logging.error(f"Statistika olishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_subscribers")
    async def admin_subscribers_handler(callback: CallbackQuery):
        await show_subscribers_page(callback, 1)

    async def show_subscribers_page(callback: CallbackQuery, page: int):
        try:
            subscribers = await get_subscribers(page=page)
            total_count = await get_subscribers_count()
            total_pages = (total_count // 10) + (1 if total_count % 10 > 0 else 0)
            text = f"👥 <b>Obuna sotib olganlar (sahifa {page}/{total_pages}):</b>\n\n"
            for sub in subscribers:
                telegram_id, subscription_date, membership_type, subscription_duration, username = sub
                text += f"• ID: {telegram_id}\n  Username: @{username or 'Noma\'lum'}\n  Sana: {subscription_date}\n  Tur: {membership_type}\n  Muddat: {subscription_duration}\n\n"
            text = text if subscribers else "Hozircha obunachilar yo'q."
            await callback.message.edit_text(text, reply_markup=get_paginated_keyboard(page, total_pages, "sub_page"))
            await callback.answer()
        except Exception as e:
            logging.error(f"Obunachilarni ko'rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data.startswith("sub_page_"))
    async def paginated_subscribers_handler(callback: CallbackQuery):
        page = int(callback.data.split("_")[2])
        await show_subscribers_page(callback, page)
    
    def get_payment_systems_keyboard():
        builder = InlineKeyboardBuilder()
        systems = ["Click", "Payme", "Uzcard", "Payeer"]
        for sys in systems:
            builder.button(text=sys, callback_data=f"add_card_system_{sys.lower()}")
        builder.button(text="⬅️ Orqaga", callback_data="admin_back")
        builder.adjust(2)
        return builder.as_markup()


    @dp.callback_query(F.data == "admin_add_card")
    async def admin_add_card_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text("💳 Qaysi to‘lov tizimiga karta qo‘shmoqchisiz?", 
                                        reply_markup=get_payment_systems_keyboard())
        await callback.answer()

    @dp.callback_query(F.data.startswith("add_card_system_"))
    async def select_card_system(callback: CallbackQuery, state: FSMContext):
        system = callback.data.replace("add_card_system_", "")
        await state.update_data(payment_system=system)
        await callback.message.edit_text(f"💳 {system.title()} uchun karta raqamini kiriting (XXXX-XXXX-XXXX-XXXX):")
        await state.set_state(AdminStates.waiting_for_card_number)
        await callback.answer()

    @dp.message(StateFilter(AdminStates.waiting_for_card_number))
    async def add_card_number_handler(message: Message, state: FSMContext):
        await state.update_data(card_number=message.text)
        await message.answer("Karta egasi ismini kiriting:")
        await state.set_state(AdminStates.waiting_for_card_holder)

    @dp.message(StateFilter(AdminStates.waiting_for_card_holder))
    async def add_card_holder_handler(message: Message, state: FSMContext):
        await state.update_data(card_holder=message.text)
        await message.answer("Amal qilish sanasini kiriting (MM/YY):")
        await state.set_state(AdminStates.waiting_for_expiry_date)

    @dp.message(StateFilter(AdminStates.waiting_for_expiry_date))
    async def add_expiry_date_handler(message: Message, state: FSMContext):
        await state.update_data(expiry_date=message.text)
        await message.answer("CVV kodini kiriting (3 raqam):")
        await state.set_state(AdminStates.waiting_for_cvv)

    @dp.message(StateFilter(AdminStates.waiting_for_cvv))
    async def add_cvv_handler(message: Message, state: FSMContext):
        data = await state.get_data()
        try:
            success = await save_card(
                data['card_number'],
                data['card_holder'],
                data['expiry_date'],
                message.text,  # cvv
                data['payment_system']  # yangi qo‘shildi
            )
            await message.answer("✅ Karta muvaffaqiyatli qo'shildi!" if success else "❌ Bu karta allaqachon mavjud!")
            await state.clear()
            await message.answer("Admin panel:", reply_markup=await get_admin_main_keyboard())
        except Exception as e:
            logging.error(f"Karta qo'shishda xato: {e}")
            await message.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_list_cards")
    async def admin_list_cards(callback: CallbackQuery):
        try:
            cards = await get_active_cards()
            if not cards:
                await callback.message.edit_text("Hozircha kartalar yo'q.", reply_markup=await get_admin_main_keyboard())
                await callback.answer()
                return

            text = "💳 <b>Saqlangan kartalar:</b>\n\n"
            builder = InlineKeyboardBuilder()
            for cid, number, holder, expiry, system in cards:
                masked = mask_card(number)
                text += f"• {system.title()} — {masked} — {holder} ({expiry})\n"
                builder.button(text=f"❌ O'chirish {system}", callback_data=f"delete_card_{cid}")

            builder.button(text="⬅️ Orqaga", callback_data="admin_back")
            builder.adjust(1)
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            await callback.answer()
        except Exception as e:
            logging.error(f"Kartalarni ko'rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data.startswith("delete_card_"))
    async def delete_card_handler(callback: CallbackQuery):
        card_id = int(callback.data.replace("delete_card_", ""))
        try:
            await delete_card(card_id)  # DB da yozish kerak
            await callback.answer("✅ Karta o‘chirildi!")
            await admin_list_cards(callback)  # ro‘yxatni yangilash
        except Exception as e:
            logging.error(f"Karta o‘chirishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")
    
    @dp.callback_query(F.data == "admin_list_plans")
    async def admin_list_plans(callback: CallbackQuery):
        try:
            plans = await get_all_plans()
            if not plans:
                await callback.message.edit_text("📌 Hozircha obunalar yo‘q.", reply_markup=await get_admin_main_keyboard())
                await callback.answer()
                return

            text = "🕒 <b>Obunalar ro‘yxati:</b>\n\n"
            builder = InlineKeyboardBuilder()
            for pid, duration, price in plans:
                text += f"• {duration} — {price} so‘m\n"
                builder.button(text=f"❌ O‘chirish {duration}", callback_data=f"delete_plan_{pid}")
            builder.button(text="⬅️ Orqaga", callback_data="admin_back")
            builder.adjust(1)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            await callback.answer()
        except Exception as e:
            logging.error(f"Obunalarni ko‘rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data.startswith("delete_plan_"))
    async def delete_plan_handler(callback: CallbackQuery):
        try:
            plan_id = int(callback.data.split("_")[2])
            await delete_plan(plan_id)
            await callback.answer("✅ Obuna o‘chirildi")
            await admin_list_plans(callback)  # ro‘yxatni yangilash
        except Exception as e:
            logging.error(f"Obuna o‘chirishda xato: {e}")
            await callback.answer("Obuna o‘chirishda xato yuz berdi.")

    @dp.callback_query(F.data == "admin_list_channels")
    async def admin_list_channels(callback: CallbackQuery):
        try:
            channels = await get_all_channels()
            if not channels:
                await callback.message.edit_text("📢 Hozircha kanallar yo‘q.", reply_markup=await get_admin_main_keyboard())
                await callback.answer()
                return

            text = "📢 <b>Kanallar ro‘yxati:</b>\n\n"
            builder = InlineKeyboardBuilder()
            for cid, channel_id, username in channels:
                text += f"• {username} ({channel_id})\n"
                builder.button(text=f"❌ O‘chirish {username}", callback_data=f"delete_channel_{cid}")
            builder.button(text="⬅️ Orqaga", callback_data="admin_back")
            builder.adjust(1)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            await callback.answer()
        except Exception as e:
            logging.error(f"Kanallarni ko‘rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data.startswith("delete_channel_"))
    async def delete_channel_handler(callback: CallbackQuery):
        try:
            channel_id = int(callback.data.split("_")[2])
            await delete_channel(channel_id)
            await callback.answer("✅ Kanal o‘chirildi")
            await admin_list_channels(callback)  # ro‘yxatni yangilash
        except Exception as e:
            logging.error(f"Kanal o‘chirishda xato: {e}")
            await callback.answer("Kanal o‘chirishda xato yuz berdi.")


    @dp.callback_query(F.data == "admin_confirmations")
    async def admin_confirmations_handler(callback: CallbackQuery):
        try:
            payments = await get_pending_payments(page=1)
            total_count = await get_pending_payments_count()
            total_pages = (total_count // 10) + (1 if total_count % 10 > 0 else 0)
            text = f"🔄 <b>Kutayotgan tasdiqlashlar (sahifa 1/{total_pages}):</b>\n\n"
            for payment in payments:
                text += f"Payment ID: {payment[0]}, User ID: {payment[1]}, Miqdor: {payment[2]} so'm, Status: {payment[3]}\n"
            text = text if payments else "Hozircha kutayotgan tasdiqlashlar yo'q."
            await callback.message.edit_text(text, reply_markup=get_paginated_keyboard(1, total_pages, "pay_page"))
            await callback.answer()
        except Exception as e:
            logging.error(f"Tasdiqlashlarni ko'rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data.startswith("pay_page_"))
    async def paginated_payments_handler(callback: CallbackQuery):
        page = int(callback.data.split("_")[2])
        try:
            payments = await get_pending_payments(page=page)
            total_count = await get_pending_payments_count()
            total_pages = (total_count // 10) + (1 if total_count % 10 > 0 else 0)
            text = f"🔄 <b>Kutayotgan tasdiqlashlar (sahifa {page}/{total_pages}):</b>\n\n"
            for payment in payments:
                text += f"Payment ID: {payment[0]}, User ID: {payment[1]}, Miqdor: {payment[2]} so'm, Status: {payment[3]}\n"
            text = text if payments else "Hozircha kutayotgan tasdiqlashlar yo'q."
            await callback.message.edit_text(text, reply_markup=get_paginated_keyboard(page, total_pages, "pay_page"))
            await callback.answer()
        except Exception as e:
            logging.error(f"To'lovlarni ko'rsatishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_membership")
    async def admin_membership_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text("⚡ Foydalanuvchi Telegram ID sini kiriting:")
        await state.set_state(AdminStates.waiting_for_membership_user)
        await callback.answer()

    @dp.message(StateFilter(AdminStates.waiting_for_membership_user))
    async def membership_user_handler(message: Message, state: FSMContext):
        try:
            user_id = int(message.text)
            await state.update_data(user_id=user_id)
            await message.answer("A'zolik turini tanlang:", reply_markup=await get_membership_keyboard(user_id))
            await state.clear()
        except ValueError:
            await message.answer("Iltimos, to'g'ri Telegram ID kiriting (raqamlar).")

    @dp.callback_query(F.data.startswith("set_mandatory_") | F.data.startswith("set_regular_"))
    async def set_membership_handler(callback: CallbackQuery):
        parts = callback.data.split("_")
        action = parts[1]
        user_id = int(parts[2])
        membership_type = 'majburiy' if action == "mandatory" else 'oddiy'
        try:
            await update_membership_type(user_id, membership_type)
            await callback.message.edit_text(
                f"A'zolik turi {membership_type} ga o'zgartirildi!",
                reply_markup=await get_admin_main_keyboard()
            )
            await callback.answer()
        except Exception as e:
            logging.error(f"A'zolik turini o'zgartirishda xato: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_set_channel")
    async def admin_set_channel_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text("📢 Kanal ID sini kiriting (masalan, -1001234567890):")
        await state.set_state(AdminStates.waiting_for_channel_id)
        await callback.answer()

    @dp.message(StateFilter(AdminStates.waiting_for_channel_id))
    async def channel_id_handler(message: Message, state: FSMContext):
        channel_id = message.text
        if not channel_id.startswith("-100"):
            await message.answer("Iltimos, to'g'ri kanal ID sini kiriting (masalan, -1001234567890).")
            return
        await state.update_data(channel_id=channel_id)
        await message.answer("Kanal username ni kiriting (masalan, @mychannel):")
        await state.set_state(AdminStates.waiting_for_channel_username)

    @dp.message(StateFilter(AdminStates.waiting_for_channel_username))
    async def channel_username_handler(message: Message, state: FSMContext):
        channel_username = message.text
        if not channel_username.startswith("@"):
            await message.answer("Iltimos, to'g'ri username kiriting (masalan, @mychannel).")
            return
        data = await state.get_data()
        try:
            success = await save_channel(data['channel_id'], channel_username)
            await message.answer("✅ Kanal muvaffaqiyatli sozlandi!" if success else "❌ Kanal saqlashda xato yuz berdi!")
            await state.clear()
            await message.answer("Admin panel:", reply_markup=await get_admin_main_keyboard())
        except Exception as e:
            logging.error(f"Kanal saqlashda xato: {e}")
            await message.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_set_plans")
    async def admin_set_plans_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text("🕒 Obuna muddatini kiriting (masalan, '2 hafta' yoki '1 yil'):")
        await state.set_state(AdminStates.waiting_for_plan_duration)
        await callback.answer()

    @dp.message(StateFilter(AdminStates.waiting_for_plan_duration))
    async def plan_duration_handler(message: Message, state: FSMContext):
        duration = message.text.strip()
        if not duration:
            await message.answer("Iltimos, muddatni kiriting (masalan, '2 hafta').")
            return
        await state.update_data(duration=duration)
        await message.answer(f"{duration} uchun narxni kiriting (so'mda):")
        await state.set_state(AdminStates.waiting_for_plan_price)

    @dp.message(StateFilter(AdminStates.waiting_for_plan_price))
    async def plan_price_handler(message: Message, state: FSMContext):
        try:
            price = float(message.text)
            if price <= 0:
                await message.answer("Iltimos, musbat narx kiriting.")
                return
            data = await state.get_data()
            success = await save_subscription_plan(data['duration'], price)
            await message.answer("✅ Plan muvaffaqiyatli qo'shildi!" if success else "❌ Plan saqlashda xato!")
            await state.clear()
            await message.answer("Admin panel:", reply_markup=await get_admin_main_keyboard())
        except ValueError:
            await message.answer("Iltimos, to'g'ri narx kiriting (raqam).")
        except Exception as e:
            logging.error(f"Obuna planini saqlashda xato: {e}")
            await message.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.callback_query(F.data == "admin_back")
    async def admin_back_handler(callback: CallbackQuery):
        await callback.message.edit_text("Admin panel:", reply_markup=await get_admin_main_keyboard())
        await callback.answer()

    @dp.message(Command("search_user"))
    async def search_user_handler(message: Message, state: FSMContext):
        await message.answer("Qidirish uchun Telegram ID, username yoki obuna muddatini kiriting:")
        await state.set_state(AdminStates.waiting_for_search_query)

    @dp.message(StateFilter(AdminStates.waiting_for_search_query))
    async def process_search_query(message: Message, state: FSMContext):
        query = message.text
        try:
            results = await search_subscribers(query)
            text = "🔍 <b>Qidiruv natijalari:</b>\n\n"
            for res in results:
                telegram_id, subscription_date, membership_type, subscription_duration, username = res
                text += f"• ID: {telegram_id}\n  Username: @{username or 'Noma\'lum'}\n  Sana: {subscription_date}\n  Tur: {membership_type}\n  Muddat: {subscription_duration}\n\n"
            text = text if results else "Hech nima topilmadi."
            await message.answer(text, reply_markup=await get_admin_main_keyboard())
            await state.clear()
        except Exception as e:
            logging.error(f"Qidiruvda xato: {e}")
            await message.answer("Xato yuz berdi. Loglarni tekshiring.")