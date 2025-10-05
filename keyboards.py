from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_subscription_plans


def get_gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="O'g'il 👨", callback_data="gender_male"),
        InlineKeyboardButton(text="Ayol 👩", callback_data="gender_female")
    )
    builder.row(
        InlineKeyboardButton(text="Egizak 👶", callback_data="gender_twin"),
        InlineKeyboardButton(text="Barchasi 🌐", callback_data="gender_all")
    )
    return builder.as_markup()


def get_duration_keyboard():
    plans = get_subscription_plans()
    builder = InlineKeyboardBuilder()
    for duration, price in plans:
        builder.row(
            InlineKeyboardButton(
                text=f"{duration} ({price} so'm)",
                callback_data=f"duration_{duration.replace(' ', '_')}"
            )
        )
    return builder.as_markup()


def get_chat_preference_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Bot orqali suhbat 🤖", callback_data="chat_bot")
    )
    builder.row(
        InlineKeyboardButton(text="Admin orqali suhbat 👤", callback_data="chat_admin")
    )
    return builder.as_markup()


def get_admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
        InlineKeyboardButton(text="💳 Karta qo'shish", callback_data="admin_add_card")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Obunachilar", callback_data="admin_subscribers"),
        InlineKeyboardButton(text="🔄 Tasdiqlashlar", callback_data="admin_confirmations")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Majburiy a'zolik", callback_data="admin_membership"),
        InlineKeyboardButton(text="📢 Kanal sozlash", callback_data="admin_set_channel")
    )
    builder.row(
        InlineKeyboardButton(text="🕒 Obuna plani qo'shish", callback_data="admin_set_plans")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()


def get_admin_confirm_keyboard(payment_id: int, user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"confirm_pay_{payment_id}_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Rad etish ❌", callback_data=f"reject_pay_{payment_id}_{user_id}")
    )
    return builder.as_markup()


def get_membership_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Majburiy qilish ⚡", callback_data=f"set_mandatory_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Oddiy qilish 🟢", callback_data=f"set_regular_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()


def get_channel_join_keyboard(channel_username: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Kanalga a'zo bo'lish 📢", url=f"https://t.me/{channel_username[1:]}")
    )
    builder.row(
        InlineKeyboardButton(text="Tekshirish 🔄", callback_data="check_membership")
    )
    return builder.as_markup()


def get_payment_method_keyboard(methods: list):
    builder = InlineKeyboardBuilder()
    for method in methods:
        builder.row(
            InlineKeyboardButton(text=method, callback_data=f"pay_{method.lower()}")
        )
    return builder.as_markup()
