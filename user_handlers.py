# user_handlers.py
from aiogram import Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ChatMember
from database import init_db, save_user, update_user_chat_preference, save_payment, get_channel, get_active_cards, get_plan_price
from keyboards import get_gender_keyboard, get_duration_keyboard, get_chat_preference_keyboard, get_channel_join_keyboard
import logging
from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import *
from states import *
def setup_user_handlers(dp: Dispatcher, bot, admin_id):
    @dp.message(Command("start"))
    async def start_handler(message: Message, state: FSMContext):
        init_db() 
        
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
        duration = callback.data.split("_")[1].replace('_', ' ')
        await state.update_data(subscription_duration=duration)
        save_user(callback.from_user.id, gender=(await state.get_data())['gender'], subscription_duration=duration)
        
        # Faol kartalarni olish
        cards = get_active_cards()
        if not cards:
            await callback.message.answer("Hozirda to'lov uchun karta mavjud emas. Admin bilan bog'laning.")
            await state.clear()
            return
        
        amount = get_plan_price(duration)
        # if amount == 0:
        #     await callback.message.answer("Obuna narxi topilmadi. Admin bilan bog'laning.")
        #     await state.clear()
        #     return
        
        # Karta ma'lumotlarini formatlash
        card_text = f"Obuna muddati: {duration}\nTo'lov miqdori: {amount} so'm\n\nQuyidagi kartaga to'lov qiling:\n"
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