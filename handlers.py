from aiogram import Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ChatMember
from database import init_db, save_user, update_user_chat_preference, save_payment, update_payment_status, save_card, get_stats, get_subscribers, get_pending_payments, update_membership_type, save_channel, get_channel, get_active_cards, DB_PATH
import sqlite3
import logging
from keyboards import *
# FSM holatlari
class BotStates(StatesGroup):
    waiting_for_gender = State()
    waiting_for_subscription_duration = State()
    waiting_for_payment_receipt = State()
    waiting_for_chat_preference = State()
    waiting_for_admin_confirmation = State()

class AdminStates(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_card_holder = State()
    waiting_for_expiry_date = State()
    waiting_for_cvv = State()
    waiting_for_membership_user = State()
    waiting_for_channel_id = State()
    waiting_for_channel_username = State()

def setup_handlers(dp: Dispatcher, bot, admin_id):
    @dp.message(Command("start"))
    async def start_handler(message: Message, state: FSMContext):
        init_db()
        if message.from_user.id == admin_id:
            await message.answer("Admin panelga xush kelibsiz!", reply_markup=get_admin_main_keyboard())
            return
        
        # Kanal a'zoligini tekshirish
        channel = get_channel()
        if not channel:
            await message.answer("Kanal hali sozlanmagan. Admin bilan bog'laning.")
            return
        channel_id, channel_username = channel
        try:
            member: ChatMember = await bot.get_chat_member(channel_id, message.from_user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                await message.answer(
                    "Botdan foydalanish uchun kanalga a'zo bo'ling!",
                    reply_markup=get_channel_join_keyboard(channel_username)
                )
                return
        except Exception as e:
            logging.error(f"Kanal tekshirish xatosi: {e}")
            await message.answer("Xato yuz berdi. Admin bilan bog'laning.")
            return
        
        await message.answer(
            "Salom! Botga xush kelibsiz.\nAvval jinsingizni tanlang:",
            reply_markup=get_gender_keyboard()
        )
        await state.set_state(BotStates.waiting_for_gender)

    @dp.callback_query(F.data == "check_membership")
    async def check_membership_handler(callback: CallbackQuery, state: FSMContext):
        channel = get_channel()
        if not channel:
            await callback.message.edit_text("Kanal hali sozlanmagan. Admin bilan bog'laning.")
            return
        channel_id, channel_username = channel
        try:
            member: ChatMember = await bot.get_chat_member(channel_id, callback.from_user.id)
            if member.status in ['member', 'administrator', 'creator']:
                await callback.message.edit_text("Rahmat! Endi botdan foydalanishingiz mumkin.")
                await callback.message.answer(
                    "Salom! Botga xush kelibsiz.\nAvval jinsingizni tanlang:",
                    reply_markup=get_gender_keyboard()
                )
                await state.set_state(BotStates.waiting_for_gender)
            else:
                await callback.answer("Hali a'zo bo'lmagansiz. Iltimos, kanalga a'zo bo'ling.")
        except Exception as e:
            logging.error(f"Kanal tekshirish xatosi: {e}")
            await callback.answer("Xato yuz berdi.")

    @dp.callback_query(StateFilter(BotStates.waiting_for_gender), F.data.startswith("gender_"))
    async def gender_handler(callback: CallbackQuery, state: FSMContext):
        gender = callback.data.split("_")[1]
        await state.update_data(gender=gender)
        await callback.message.answer(
            f"Jinsingiz: {gender.capitalize()}\n\nEndi obuna muddatini tanlang:",
            reply_markup=get_duration_keyboard()
        )
        await state.set_state(BotStates.waiting_for_subscription_duration)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(StateFilter(BotStates.waiting_for_subscription_duration), F.data.startswith("duration_"))
    async def duration_handler(callback: CallbackQuery, state: FSMContext):
        duration = callback.data.split("_")[1]
        duration_map = {
            "1month": "1 oy",
            "3months": "3 oy",
            "6months": "6 oy"
        }
        subscription_duration = duration_map[duration]
        await state.update_data(subscription_duration=subscription_duration)
        save_user(callback.from_user.id, gender=(await state.get_data())['gender'], subscription_duration=subscription_duration)
        
        # Faol kartalarni olish
        cards = get_active_cards()
        if not cards:
            await callback.message.answer("Hozirda to'lov uchun karta mavjud emas. Admin bilan bog'laning.")
            await state.clear()
            return
        
        duration_prices = {
            "1 oy": 100000,
            "3 oy": 250000,
            "6 oy": 450000
        }
        amount = duration_prices.get(subscription_duration, 100000)
        
        # Karta ma'lumotlarini formatlash
        card_text = f"Obuna muddati: {subscription_duration}\nTo'lov miqdori: {amount} so'm\n\nQuyidagi kartaga to'lov qiling:\n"
        for card in cards:
            card_text += f"💳 Karta: {card[0]}\nEgasi: {card[1]}\nAmal qilish muddati: {card[2]}\n\n"
        card_text += "To'lov qilib bo'lgach, chekni (rasm yoki hujjat) yuboring:"
        
        await callback.message.answer(card_text)
        await state.set_state(BotStates.waiting_for_payment_receipt)
        await callback.message.delete()
        await callback.answer()

    @dp.message(StateFilter(BotStates.waiting_for_payment_receipt), F.photo | F.document)
    async def payment_receipt_handler(message: Message, state: FSMContext):
        receipt_id = message.photo[-1].file_id if message.photo else message.document.file_id
        data = await state.get_data()
        duration_prices = {
            "1 oy": 100000,
            "3 oy": 250000,
            "6 oy": 450000
        }
        amount = duration_prices.get(data.get('subscription_duration', '1 oy'), 100000)
        payment_id = save_payment(message.from_user.id, amount, receipt_id)
        
        username = message.from_user.username or "Noma'lum"
        admin_text = (
            f"Yangi to'lov:\n"
            f"Username: @{username}\n"
            f"Jins: {data.get('gender', 'Noma\'lum').capitalize()}\n"
            f"Muddat: {data.get('subscription_duration', 'Noma\'lum')}\n"
            f"User ID: {message.from_user.id}\n"
            f"Miqdor: {amount} so'm\n"
            f"Payment ID: {payment_id}\n\n"
            f"Tasdiqlang:"
        )
        
        if message.photo:
            await bot.send_photo(admin_id, receipt_id, caption=admin_text, reply_markup=get_admin_confirm_keyboard(payment_id, message.from_user.id))
        else:
            await bot.send_document(admin_id, receipt_id, caption=admin_text, reply_markup=get_admin_confirm_keyboard(payment_id, message.from_user.id))
        
        await message.answer(
            f"To'lov chekingiz qabul qilindi ({amount} so'm). Admin tasdiqlaydi.\n\nSuhbatni qanday o'tkazmoqchisiz?",
            reply_markup=get_chat_preference_keyboard()
        )
        await state.set_state(BotStates.waiting_for_chat_preference)

    @dp.callback_query(StateFilter(BotStates.waiting_for_chat_preference), F.data.startswith("chat_"))
    async def chat_preference_handler(callback: CallbackQuery, state: FSMContext):
        preference = callback.data.split("_")[1]
        data = await state.get_data()
        data['chat_preference'] = preference
        await state.update_data(**data)
        update_user_chat_preference(callback.from_user.id, preference)
        await callback.message.answer(
            f"Suhbat usuli: {preference.capitalize()}\n\nEndi admin to'lovni tasdiqlaydi. Iltimos kuting."
        )
        await state.set_state(BotStates.waiting_for_admin_confirmation)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data.startswith("confirm_pay_") | F.data.startswith("reject_pay_"))
    async def admin_payment_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        parts = callback.data.split("_")
        action = parts[1]
        payment_id = int(parts[2])
        user_id = int(parts[3])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        payment = cursor.execute("SELECT amount FROM payments WHERE id=?", (payment_id,)).fetchone()
        conn.close()
        
        if not payment:
            await callback.answer("To'lov topilmadi!")
            return
        
        amount = payment[0]
        status = 'confirmed' if action == "confirm" else 'rejected'
        membership_type = 'majburiy' if action == "confirm" and amount > 200000 else 'oddiy'
        
        try:
            update_payment_status(payment_id, status, user_id, membership_type)
            await bot.send_message(user_id, "To'lov tasdiqlandi! Obuna faollashtirildi." if action == "confirm" else "To'lov rad etildi. Qayta urinib ko'ring.")
            await callback.message.edit_caption(
                caption=callback.message.caption + ("\n\n✅ Tasdiqlandi!" if action == "confirm" else "\n\n❌ Rad etildi!"),
                reply_markup=None
            )
            await callback.answer()
        except Exception as e:
            logging.error(f"To'lov tasdiqlash xatosi: {e}")
            await callback.answer("Xato yuz berdi. Loglarni tekshiring.")

    @dp.message(Command("admin"))
    async def admin_handler(message: Message):
        if message.from_user.id != admin_id:
            await message.answer("Siz admin emassiz!")
            return
        await message.answer("Admin panel:", reply_markup=get_admin_main_keyboard())

    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        total_users, total_payments, total_revenue, mandatory_members = get_stats()
        stats_text = f"""📊 <b>Statistika:</b>
👥 Faol obunachilar: {total_users}
💰 Tasdiqlangan to'lovlar soni: {total_payments}
💵 Umumiy daromad: {total_revenue} so'm
⚡ Majburiy a'zolik: {mandatory_members} ta"""
        await callback.message.edit_text(stats_text, reply_markup=get_admin_main_keyboard())
        await callback.answer()

    @dp.callback_query(F.data == "admin_subscribers")
    async def admin_subscribers_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        subscribers = get_subscribers()
        text = "👥 <b>Obuna sotib olganlar:</b>\n\n"
        for sub in subscribers:
            text += f"• ID: {sub[0]}\n  Sana: {sub[1]}\n  Tur: {sub[2]}\n  Muddat: {sub[3]}\n\n"
        text = text if subscribers else "Hozircha obunachilar yo'q."
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())
        await callback.answer()

    @dp.callback_query(F.data == "admin_add_card")
    async def admin_add_card_handler(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        await callback.message.edit_text("💳 Karta qo'shish:\nKarta raqamini kiriting (XXXX-XXXX-XXXX-XXXX):")
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
        success = save_card(data['card_number'], data['card_holder'], data['expiry_date'], message.text)
        await message.answer("✅ Karta muvaffaqiyatli qo'shildi!" if success else "❌ Bu karta raqami allaqachon mavjud!")
        await state.clear()
        await message.answer("Admin panel:", reply_markup=get_admin_main_keyboard())

    @dp.callback_query(F.data == "admin_confirmations")
    async def admin_confirmations_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        payments = get_pending_payments()
        text = "🔄 <b>Kutayotgan tasdiqlashlar:</b>\n\n"
        for payment in payments:
            text += f"Payment ID: {payment[0]}, User ID: {payment[1]}, Miqdor: {payment[2]} so'm, Status: {payment[3]}\n"
        text = text if payments else "Hozircha kutayotgan tasdiqlashlar yo'q."
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())
        await callback.answer()

    @dp.callback_query(F.data == "admin_membership")
    async def admin_membership_handler(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        await callback.message.edit_text("⚡ Foydalanuvchi Telegram ID sini kiriting:")
        await state.set_state(AdminStates.waiting_for_membership_user)
        await callback.answer()

    @dp.message(StateFilter(AdminStates.waiting_for_membership_user))
    async def membership_user_handler(message: Message, state: FSMContext):
        try:
            user_id = int(message.text)
            await state.update_data(user_id=user_id)
            await message.answer("A'zolik turini tanlang:", reply_markup=get_membership_keyboard(user_id))
            await state.clear()
        except ValueError:
            await message.answer("Iltimos, to'g'ri Telegram ID kiriting (raqamlar).")

    @dp.callback_query(F.data.startswith("set_mandatory_") | F.data.startswith("set_regular_"))
    async def set_membership_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        parts = callback.data.split("_")
        action = parts[1]
        user_id = int(parts[2])
        membership_type = 'majburiy' if action == "mandatory" else 'oddiy'
        update_membership_type(user_id, membership_type)
        await callback.message.edit_text(f"A'zolik turi {membership_type} ga o'zgartirildi!", reply_markup=get_admin_main_keyboard())
        await callback.answer()

    @dp.callback_query(F.data == "admin_set_channel")
    async def admin_set_channel_handler(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
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
        success = save_channel(data['channel_id'], channel_username)
        await message.answer("✅ Kanal muvaffaqiyatli sozlandi!" if success else "❌ Kanal saqlashda xato yuz berdi!")
        await state.clear()
        await message.answer("Admin panel:", reply_markup=get_admin_main_keyboard())

    @dp.callback_query(F.data == "admin_back")
    async def admin_back_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        await callback.message.edit_text("Admin panel:", reply_markup=get_admin_main_keyboard())
        await callback.answer()