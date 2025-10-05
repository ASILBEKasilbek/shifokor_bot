from aiogram.fsm.state import State, StatesGroup

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
    waiting_for_plan_price = State()
    waiting_for_plan_duration = State()