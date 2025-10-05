from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_subscription_plans

async def get_gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="O'g'il 👨", callback_data="gender_male")
    builder.button(text="Ayol 👩", callback_data="gender_female")
    builder.button(text="Egizak 👶", callback_data="gender_twin")
    builder.button(text="Barchasi 🌐", callback_data="gender_all")
    builder.adjust(2)
    return builder.as_markup()

async def get_duration_keyboard():
    builder = InlineKeyboardBuilder()
    plans = await get_subscription_plans()  # Asinxron chaqiruv
    if not plans:
        builder.button(text="Obuna planlari mavjud emas", callback_data="no_plans")
    else:
        for duration, price in plans:
            builder.button(
                text=f"{duration} ({price} so'm)",
                callback_data=f"duration_{duration.replace(' ', '_')}"
            )
    builder.adjust(2)
    return builder.as_markup()

async def get_chat_preference_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Bot orqali suhbat 🤖", callback_data="chat_bot")
    builder.button(text="Admin orqali suhbat 👤", callback_data="chat_admin")
    builder.adjust(2)
    return builder.as_markup()

async def get_admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="admin_stats")
    builder.button(text="💳 Karta qo'shish", callback_data="admin_add_card")
    builder.button(text="👥 Obunachilar", callback_data="admin_subscribers")
    builder.button(text="🔄 Tasdiqlashlar", callback_data="admin_confirmations")
    builder.button(text="📢 Kanal qo'shish", callback_data="admin_set_channel")
    builder.button(text="🕒 Obuna plani qo'shish", callback_data="admin_set_plans")
    builder.button(text="🔙 Orqaga", callback_data="admin_back")
    builder.adjust(2)
    return builder.as_markup()

async def get_admin_confirm_keyboard(payment_id: int, user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Tasdiqlash ✅", callback_data=f"confirm_pay_{payment_id}_{user_id}")
    builder.button(text="Rad etish ❌", callback_data=f"reject_pay_{payment_id}_{user_id}")
    builder.adjust(2)
    return builder.as_markup()

async def get_membership_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Majburiy qilish ⚡", callback_data=f"set_mandatory_{user_id}")
    builder.button(text="Oddiy qilish 🟢", callback_data=f"set_regular_{user_id}")
    builder.button(text="🔙 Orqaga", callback_data="admin_back")
    builder.adjust(2)
    return builder.as_markup()

async def get_channel_join_keyboard(channel_username: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="Kanalga a'zo bo'lish 📢", url=f"https://t.me/{channel_username[1:]}")
    builder.button(text="Tekshirish 🔄", callback_data="check_membership")
    builder.adjust(1)
    return builder.as_markup()

async def get_payment_method_keyboard(methods: list):
    builder = InlineKeyboardBuilder()
    for method in methods:
        builder.button(text=method, callback_data=f"pay_{method.lower()}")
    builder.adjust(2)
    return builder.as_markup()
async def get_renew_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Obunani yangilash", callback_data="start_gender")
    builder.adjust(1)
    return builder.as_markup()