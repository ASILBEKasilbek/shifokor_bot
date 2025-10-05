from aiogram import Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ChatMember, InlineKeyboardButton
from database import (
    init_db, save_user, update_user_chat_preference, save_payment,
    get_channel, get_active_cards, get_plan_price
)
from keyboards import (
    get_gender_keyboard, get_duration_keyboard, get_chat_preference_keyboard,
    get_channel_join_keyboard, get_admin_confirm_keyboard
)
from states import BotStates
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging


def setup_user_handlers(dp: Dispatcher, bot, admin_id):
    logging.basicConfig(level=logging.INFO)

    # --- Start handler ---
    @dp.message(Command("start"))
    async def start_handler(message: Message, state: FSMContext):
        init_db()
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

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Aniqlash", callback_data="start_gender"))

        await message.answer(
            "Salom! Bu bot yordamida jinsni taxmin qilish va pullik xizmatlardan foydalanasiz.",
            reply_markup=builder.as_markup()
        )
        await state.clear()

    # --- Kanal a'zoligini tekshirish ---
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

                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text="Aniqlash", callback_data="start_gender"))

                await callback.message.answer(
                    "Salom! Bu bot yordamida jinsni taxmin qilish va pullik xizmatlardan foydalanasiz.",
                    reply_markup=builder.as_markup()
                )
                await state.clear()
            else:
                await callback.answer("Hali a'zo bo'lmagansiz. Iltimos, kanalga a'zo bo'ling.", show_alert=True)
        except Exception as e:
            logging.error(f"Kanal tekshirish xatosi: {e}")
            await callback.answer("Xato yuz berdi.")
        await callback.answer()

    # --- Gender tanlash start ---
    @dp.callback_query(F.data == "start_gender")
    async def start_gender_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text(
            "Iltimos, jinsingizni tanlang:",
            reply_markup=get_gender_keyboard()
        )
        await state.set_state(BotStates.waiting_for_gender)
        await callback.answer()

    # --- Gender handler ---
    @dp.callback_query(StateFilter(BotStates.waiting_for_gender), F.data.startswith("gender_"))
    async def gender_handler(callback: CallbackQuery, state: FSMContext):
        gender = callback.data.split("_")[1]
        await state.update_data(gender=gender)
        await callback.message.edit_text(
            f"Jinsingiz: {gender.capitalize()}\n\nEndi obuna muddatini tanlang:",
            reply_markup=get_duration_keyboard()
        )
        await state.set_state(BotStates.waiting_for_subscription_duration)
        await callback.answer()

    # --- Subscription duration ---
    @dp.callback_query(StateFilter(BotStates.waiting_for_subscription_duration), F.data.startswith("duration_"))
    async def duration_handler(callback: CallbackQuery, state: FSMContext):
        duration = callback.data.split("_", 1)[1].replace('_', ' ')
        await state.update_data(subscription_duration=duration)
        data = await state.get_data()
        save_user(callback.from_user.id, gender=data['gender'], subscription_duration=duration)

        amount = get_plan_price(duration)
        cards = get_active_cards()
        if not cards:
            await callback.message.edit_text("Hozirda to'lov uchun karta mavjud emas. Admin bilan bog'laning.")
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for method in ['Click', 'Payme', 'Uzcard', 'Payeer']:
            builder.row(InlineKeyboardButton(text=method, callback_data=f"pay_{method.lower()}"))
        builder.row(InlineKeyboardButton(text="Orqaga", callback_data="back_to_duration"))

        card_text = (
            f"💳 To'lov ko'rsatmasi\n"
            f"Jins: {data['gender'].capitalize()}\n"
            f"Tarif: {duration}\n"
            f"To'lov summasi: {amount} so'm\n\n"
            f"Quyidagi tugmalar orqali to'lov usulini tanlang:"
        )
        await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
        await state.set_state(BotStates.waiting_for_payment_method)
        await callback.answer()

    # --- To'lov usulini tanlash ---
    @dp.callback_query(StateFilter(BotStates.waiting_for_payment_method), F.data.startswith("pay_"))
    async def payment_method_handler(callback: CallbackQuery, state: FSMContext):
        method = callback.data.split("_")[1]
        data = await state.get_data()
        amount = get_plan_price(data.get('subscription_duration', '1 oy'))
        cards = get_active_cards()
        print(cards)# cards=[('1234-1234-1234-1234', 'Asilbek', '12/27')]

        
        card_info = cards[-1] if cards else None
        print(card_info)
        if card_info:
            card_text = (
                f"✅ Tanlangan to'lov usuli: {method.capitalize()}\n"
                f"💳 Karta: {card_info[0]}\n"
                f"👤 Egasi: {card_info[1]}\n"
                f"⏳ Amal qilish muddati: {card_info[2]}\n\n"
                f"To'lov qilganingizdan so'ng, chekni (rasm yoki hujjat) yuboring."
            )

            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="To'lov qildim", callback_data="paid"))
            builder.row(InlineKeyboardButton(text="Orqaga", callback_data="back_to_duration"))

            await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
            await state.set_state(BotStates.waiting_for_payment_receipt)
        else:
            await callback.message.edit_text("Tanlangan usul uchun karta mavjud emas. Boshqa usulni tanlang.")
        await callback.answer()

    # --- To'lov qildim va Orqaga tugmalar ---
    @dp.callback_query(StateFilter(BotStates.waiting_for_payment_receipt), F.data.in_({"paid", "back_to_duration"}))
    async def payment_confirmation_handler(callback: CallbackQuery, state: FSMContext):
        if callback.data == "back_to_duration":
            await callback.message.edit_text("Obuna muddatini tanlang:", reply_markup=get_duration_keyboard())
            await state.set_state(BotStates.waiting_for_subscription_duration)
        elif callback.data == "paid":
            await callback.message.edit_text("Iltimos, to'lov chekini rasm yoki hujjat sifatida yuboring:")
        await callback.answer()

    # --- Payment receipt ---
    @dp.message(StateFilter(BotStates.waiting_for_payment_receipt), F.photo | F.document)
    async def payment_receipt_handler(message: Message, state: FSMContext):
        receipt_id = message.photo[-1].file_id if message.photo else message.document.file_id
        data = await state.get_data()
        amount = get_plan_price(data.get('subscription_duration', '1 oy'))
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

        try:
            if message.photo:
                await bot.send_photo(admin_id, receipt_id, caption=admin_text,
                                     reply_markup=get_admin_confirm_keyboard(payment_id, message.from_user.id))
            else:
                await bot.send_document(admin_id, receipt_id, caption=admin_text,
                                        reply_markup=get_admin_confirm_keyboard(payment_id, message.from_user.id))
        except Exception as e:
            logging.error(f"Chek yuborish xatosi: {e}")
            await message.answer("Chekni admin ga yuborishda xato yuz berdi. Admin bilan bog'laning.")
            await state.clear()
            return

        await message.answer(
            f"To'lov chekingiz qabul qilindi ({amount} so'm). Admin tasdiqlaydi.\n\nSuhbatni qanday o'tkazmoqchisiz?",
            reply_markup=get_chat_preference_keyboard()
        )
        await state.set_state(BotStates.waiting_for_chat_preference)

    # --- Chat preference ---
    @dp.callback_query(StateFilter(BotStates.waiting_for_chat_preference), F.data.startswith("chat_"))
    async def chat_preference_handler(callback: CallbackQuery, state: FSMContext):
        preference = callback.data.split("_")[1]
        data = await state.get_data()
        data['chat_preference'] = preference
        await state.update_data(**data)

        try:
            update_user_chat_preference(callback.from_user.id, preference)
        except Exception as e:
            logging.error(f"Suhbat usulini saqlash xatosi: {e}")
            await callback.message.answer("Xato yuz berdi. Admin bilan bog'laning.")
            await state.clear()
            return

        await callback.message.answer(
            f"Suhbat usuli: {preference.capitalize()}\n\nEndi admin to'lovni tasdiqlaydi. Iltimos kuting."
        )
        await state.set_state(BotStates.waiting_for_admin_confirmation)
        await callback.message.delete()
        await callback.answer()
