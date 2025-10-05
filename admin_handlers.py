from aiogram import Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from database import get_stats, get_subscribers, get_pending_payments, update_membership_type, save_channel, save_card, update_payment_status, save_subscription_plan, get_subscription_plans
from keyboards import get_admin_main_keyboard, get_admin_confirm_keyboard, get_membership_keyboard
from states import AdminStates
import sqlite3
from database import DB_PATH
import logging

def setup_admin_handlers(dp: Dispatcher, bot, admin_id):
    @dp.message(Command("admin"))
    async def admin_handler(message: Message):
        if message.from_user.id != admin_id:
            await message.answer("Siz admin emassiz!")
            return
        await message.answer("Admin panel:", reply_markup=get_admin_main_keyboard())

    @dp.callback_query(F.data.startswith("confirm_pay_") | F.data.startswith("reject_pay_"))
    async def admin_payment_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        parts = callback.data.split("_")
        action = parts[0]
        print(action)
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

    @dp.callback_query(F.data == "admin_set_plans")
    async def admin_set_plans_handler(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
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
            success = save_subscription_plan(data['duration'], price)
            await message.answer("✅ Plan muvaffaqiyatli qo'shildi!" if success else "❌ Plan saqlashda xato!")
            await state.clear()
            await message.answer("Admin panel:", reply_markup=get_admin_main_keyboard())
        except ValueError:
            await message.answer("Iltimos, to'g'ri narx kiriting (raqam).")

    @dp.callback_query(F.data == "admin_back")
    async def admin_back_handler(callback: CallbackQuery):
        if callback.from_user.id != admin_id:
            await callback.answer("Ruxsat yo'q!")
            return
        await callback.message.edit_text("Admin panel:", reply_markup=get_admin_main_keyboard())
        await callback.answer()