from email.mime import message
from aiogram import Dispatcher, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ChatMember
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    save_user, update_user_chat_preference, save_payment,
    get_channel, get_active_cards, get_plan_price, get_user_subscription
)
from keyboards import (
    get_gender_keyboard, get_duration_keyboard, get_chat_preference_keyboard,
    get_channel_join_keyboard, get_admin_confirm_keyboard
)
from states import BotStates
import logging
from datetime import datetime

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_user_handlers(dp: Dispatcher, bot: Bot, admin_id: int):
    @dp.message(Command("start"))
    async def start_handler(message: Message, state: FSMContext):
        channel = await get_channel()
        # Agar kanal mavjud bo'lsa - tekshirish
        if channel:
            channel_id, channel_username = channel
            try:
                member: ChatMember = await bot.get_chat_member(chat_id=channel_id, user_id=message.from_user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    await message.answer(
                        f"Kanalga a'zo bo'ling: {channel_username}",
                        reply_markup=await get_channel_join_keyboard(channel_username)
                    )
                    return
            except Exception as e:
                logging.error(f"Kanal a'zoligini tekshirishda xato: {e}")
                # Kanal bor, lekin tekshirib bo'lmadi — baribir davom etadi

        # Kanal yo'q yoki foydalanuvchi tekshiruvdan o'tgan bo'lsa - davom etadi
        subscription = await get_user_subscription(message.from_user.id)
        if subscription and subscription[3]:  # is_active == 1
            duration, sub_date, expiry_date, _ = subscription
            await message.answer(
                f"✅ Obuna faollashtirilgan!\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📦 Tarif: {duration}\n"
                f"📅 Boshlangan sana: {sub_date}\n"
                f"⏳ Tugash sanasi:{expiry_date} gacha!\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"🤝 Qo‘llab-quvvatlash bilan bog'lanish uchun pastdagi tugmani bosing va o'zingizga kerakli savolni berib unga javob oling!"
            )
        else:
            builder = InlineKeyboardBuilder()
            builder.button(text="Aniqlash", callback_data="start_gender")
            builder.adjust(1)
            await message.answer(
                "👋 Salom! Bu bot yordamida jinsni taxmin qilish va pullik xizmatlardan foydalanasiz.\n\n🔎 Aniqlash tugmasini bosing.",
                reply_markup=builder.as_markup()
            )

        await state.clear()

    @dp.callback_query(F.data == "check_membership")
    async def check_membership_handler(callback: CallbackQuery, state: FSMContext):
        channel = await get_channel()
        if not channel:
            await callback.message.edit_text("Kanal hali sozlanmagan. Admin bilan bog'laning.")
            return

        channel_id, channel_username = channel
        try:
            member: ChatMember = await bot.get_chat_member(chat_id=channel_id, user_id=callback.from_user.id)
            if member.status in ['member', 'administrator', 'creator']:
                # Check subscription status
                subscription = await get_user_subscription(callback.from_user.id)
                if subscription and subscription[3]:  # is_active == 1
                    duration, sub_date, expiry_date, _ = subscription
                    await message.answer(
                        f"✅ Obuna faollashtirilgan!\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 Tarif: {duration}\n"
                        f"📅 Boshlangan sana: {sub_date}\n"
                        f"⏳ Tugash sanasi:{expiry_date} gacha!\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"🤝 Qo‘llab-quvvatlash bilan bog'lanish uchun pastdagi tugmani bosing va o'zingizga kerakli savolni berib unga javob oling!"
                    )
                else:
                    builder = InlineKeyboardBuilder()
                    builder.button(text="Aniqlash", callback_data="start_gender")
                    builder.adjust(1)
                    await callback.message.edit_text(
                        "Rahmat! Endi botdan foydalanishingiz mumkin.",
                        reply_markup=builder.as_markup()
                    )
                await state.clear()
            else:
                await callback.answer("Hali kanalga a'zo bo'lmagansiz. Iltimos, a'zo bo'ling.", show_alert=True)
        except Exception as e:
            logging.error(f"Kanal tekshirish xatosi: {e}")
            await callback.answer("Xato yuz berdi. Admin bilan bog'laning.")
        await callback.answer()

    @dp.callback_query(F.data == "start_gender")
    async def start_gender_handler(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text(
            """🤍 Assalomu alaykum, bo‘lajak ona!\n\nQaysi yo‘nalishda bilib olmoqchisiz?""",
            reply_markup=await get_gender_keyboard()
        )
        await state.set_state(BotStates.waiting_for_gender)
        await callback.answer()

    @dp.callback_query(StateFilter(BotStates.waiting_for_gender), F.data.startswith("gender_"))
    async def gender_handler(callback: CallbackQuery, state: FSMContext):
        gender = callback.data.split("_")[1]
        await state.update_data(gender=gender)
        a = (
            "🧒" if gender == "female" 
            else "👶" if gender == "twin" 
            else "👦" if gender == "male" 
            else "👨‍👩‍👧‍👦" if gender == "all" 
            else "❓"
        )

        b = (
            "O'g'il" if gender == "male" 
            else "Qiz" if gender == "female" 
            else "Egizak" if gender == "twin" 
            else "Barchasi" if gender == "all" 
            else "Noma’lum"
        )

        await callback.message.edit_text(
            f"🍼 Jins tanlandi: {b}  {a}\n\n📆 Endi o'zingizga kerakli muddatni tanlang: 👇",
            reply_markup=await get_duration_keyboard()
        )
        await state.set_state(BotStates.waiting_for_subscription_duration)
        await callback.answer()

    @dp.callback_query(StateFilter(BotStates.waiting_for_subscription_duration), F.data.startswith("duration_"))
    async def duration_handler(callback: CallbackQuery, state: FSMContext):
        duration = callback.data.split("_", 1)[1].replace('_', ' ')
        await state.update_data(subscription_duration=duration)
        data = await state.get_data()
        try:
            await save_user(
                telegram_id=callback.from_user.id,
                gender=data['gender'],
                subscription_duration=duration,
                username=callback.from_user.username
            )
        except Exception as e:
            logging.error(f"Foydalanuvchi saqlashda xato: {e}")
            await callback.message.edit_text("Ma'lumotlarni saqlashda xato yuz berdi. Admin bilan bog'laning.")
            return

        amount = await get_plan_price(duration)
        cards = await get_active_cards()
        if not cards:
            await callback.message.edit_text("Hozirda to'lov uchun karta mavjud emas. Admin bilan bog'laning.")
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for method in ['Click', 'Payme', 'Uzcard', 'Payeer']:
            builder.button(text=method, callback_data=f"pay_{method.lower()}")
        builder.button(text="Orqaga", callback_data="back_to_duration")
        builder.adjust(2)
        a="O'g'il" if data['gender'] == "male" else "Qiz" if data['gender'] == "female" else "Egizak"
        b="👦" if data['gender'] == "male" else "🧒" if data['gender'] == "female" else "👶"
        print(amount)
        card_text = (
            f"💳 To‘lov ko‘rsatmasi:\n"
            f"👶 Tanlangan Jins: {a} {b}\n"
            f"📦 Tanlangan tarif: {duration}\n"
            f"💰 To‘lov summasi: {amount} narx so'm\n\n"
            f"💡 Quyidagi tugmalar orqali to‘lov usulini tanlang: 👇"
        )
        await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
        await state.set_state(BotStates.waiting_for_payment_method)
        await callback.answer()

    @dp.callback_query(StateFilter(BotStates.waiting_for_payment_method), F.data.startswith("pay_"))
    async def payment_method_handler(callback: CallbackQuery, state: FSMContext):
        method = callback.data.split("_")[1]
        data = await state.get_data()
        amount = await get_plan_price(data.get('subscription_duration', '1 oy'))
        cards = await get_active_cards()

        card_info = None
        for card in cards:
            if method.lower() == card[4].lower():
                card_info = card
                break
            card_info=card

            

        if card_info:
            card_text = (
                f"✅ Tanlangan to'lov usuli: #{method.capitalize()}\n"
                f"💳 Karta: ``` {card_info[1]}```\n"
                f"👤 Egasi: {card_info[2]}\n\n"
                f"To'lov qilganingizdan so'ng, chekni rasmini yuboring ✅"
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="To'lov qildim", callback_data="paid")
            builder.button(text="Orqaga", callback_data="back_to_duration")
            builder.adjust(2)

            await callback.message.edit_text(card_text, reply_markup=builder.as_markup(),parse_mode="Markdown")
            await state.set_state(BotStates.waiting_for_payment_receipt)
        else:
            await callback.message.edit_text(f"{method.capitalize()} uchun karta mavjud emas. Boshqa usulni tanlang.")
        await callback.answer()

    @dp.callback_query(StateFilter(BotStates.waiting_for_payment_receipt), F.data.in_({"paid", "back_to_duration"}))
    async def payment_confirmation_handler(callback: CallbackQuery, state: FSMContext):
        if callback.data == "back_to_duration":
            await callback.message.edit_text(
                "Obuna muddatini tanlang:",
                reply_markup=await get_duration_keyboard()
            )
            await state.set_state(BotStates.waiting_for_subscription_duration)
        elif callback.data == "paid":
            await callback.message.edit_text("Iltimos, to'lov chekini rasm yoki hujjat sifatida yuboring:")
        await callback.answer()

    @dp.message(StateFilter(BotStates.waiting_for_payment_receipt), F.photo | F.document)
    async def payment_receipt_handler(message: Message, state: FSMContext):
        receipt_id = message.photo[-1].file_id if message.photo else message.document.file_id
        data = await state.get_data()
        amount = await get_plan_price(data.get('subscription_duration', '1 oy'))
        try:
            payment_id = await save_payment(message.from_user.id, amount, receipt_id)
        except Exception as e:
            logging.error(f"To'lov saqlashda xato: {e}")
            await message.answer("To'lovni saqlashda xato yuz berdi. Admin bilan bog'laning.")
            return

        username = message.from_user.username or "Noma'lum"
        admin_text = (
            f"Yangi to'lov:\n"
            f"Username: @{username}\n"
            f"Jins: {data.get('gender', "Noma'lum").capitalize()}\n"
            f"Muddat: {data.get('subscription_duration', 'Noma\'lum')}\n"
            f"User ID: {message.from_user.id}\n"
            f"Miqdor: {amount} so'm\n"
            f"Payment ID: {payment_id}\n\n"
            f"Tasdiqlang:"
        )

        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=receipt_id,
                    caption=admin_text,
                    reply_markup=await get_admin_confirm_keyboard(payment_id, message.from_user.id)
                )
            else:
                await bot.send_document(
                    chat_id=admin_id,
                    document=receipt_id,
                    caption=admin_text,
                    reply_markup=await get_admin_confirm_keyboard(payment_id, message.from_user.id)
                )
        except Exception as e:
            logging.error(f"Chek yuborish xatosi: {e}")
            await message.answer("Chekni admin ga yuborishda xato yuz berdi. Admin bilan bog'laning.")
            await state.clear()
            return

        subscription = await get_user_subscription(message.from_user.id)
        if subscription:
            duration, sub_date, expiry_date, _ = subscription
            await message.answer(
                f"✅ To'lov chekingiz qabul qilindi ({amount} so'm).\n"
                f"➕ Obuna ma'lumotlari:\n"
                f"📦 Tarif: {duration}\n"
                f"📍 Boshlangan sana: {sub_date}\n"
                f"📌 Tugash sanasi: {expiry_date}\n\n"
                f"⏳ Holat: Kutmoqda\n\n"
                f"⏳ Qabul qilindi!\n\n"
                f"To'lovingiz 5 daqiqadan 2 soatgacha bo'lgan vaqt ichida amalga oshiriladi!")
        else:
            await message.answer(f"To'lov chekingiz qabul qilindi ({amount} so'm). Admin tasdiqlaydi.\n\nSuhbatni qanday o'tkazmoqchisiz?")
        await state.set_state(BotStates.waiting_for_chat_preference)

    @dp.callback_query(StateFilter(BotStates.waiting_for_chat_preference), F.data.startswith("chat_"))
    async def chat_preference_handler(callback: CallbackQuery, state: FSMContext):
        preference = callback.data.split("_")[1]
        data = await state.get_data()
        data['chat_preference'] = preference
        await state.update_data(**data)

        try:
            await update_user_chat_preference(callback.from_user.id, preference)
        except Exception as e:
            logging.error(f"Suhbat usulini saqlash xatosi: {e}")
            await callback.message.answer("Xato yuz berdi. Admin bilan bog'laning.")
            await state.clear()
            return

        subscription = await get_user_subscription(callback.from_user.id)
        if subscription:
            duration, sub_date, expiry_date, is_active = subscription
            status = "Faol" if is_active else "Kutmoqda"
            await callback.message.answer(
                f"Suhbat usuli: {preference.capitalize()}\n"
                f"Obuna ma'lumotlari:\n"
                f"Tarif: {duration}\n"
                f"Boshlangan sana: {sub_date}\n"
                f"Tugash sanasi: {expiry_date}\n"
                f"Holat: {status}\n\n"
                f"Endi admin to'lovni tasdiqlaydi. Iltimos kuting."
            )
        else:
            await callback.message.answer(
                f"Suhbat usuli: {preference.capitalize()}\n\nEndi admin to'lovni tasdiqlaydi. Iltimos kuting."
            )
        await state.set_state(BotStates.waiting_for_admin_confirmation)
        await callback.message.delete()
        await callback.answer()