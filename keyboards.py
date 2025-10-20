from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

def get_user_type_keyboard():
    keyboard = [
        ['👨‍🏫 Я тренер', '👤 Я ученик']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_confirm_keyboard():
    keyboard = [
        ['✅ Да, все верно', '❌ Нет, исправить вручную']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_meal_type_keyboard():
    keyboard = [
        ['🍳 Завтрак', '🍲 Обед'],
        ['🍰 Перекус', '🍽️ Ужин']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_yes_no_keyboard():
    keyboard = [
        ['✅ Да', '❌ Нет']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def remove_keyboard():
    return ReplyKeyboardRemove()
