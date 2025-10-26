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

def get_drink_method_keyboard():
    keyboard = [
        ['📝 Ввести название напитка']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_drink_categories_keyboard():
    keyboard = [
        ['💧 Вода', '🥤 Газировка', '☕ Кофе/Чай'],
        ['🧃 Сок', '🥛 Молочное', '🍺 Алкоголь'],
        ['⚡ Энергетик', '🏃‍♂️ Спортивное', '📝 Другое']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_popular_drinks_keyboard():
    keyboard = [
        ['💧 Вода', '🥤 Кола', '☕ Кофе'],
        ['🧃 Апельсиновый сок', '🥛 Молоко', '🍺 Пиво'],
        ['⚡ Red Bull', '🏃‍♂️ Изотоник', '📝 Другой напиток']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_drink_volumes_keyboard():
    keyboard = [
        ['🥤 250мл (стакан)', '🥤 330мл (банка)'],
        ['🥤 500мл (бутылка)', '🥤 1000мл (литр)'],
        ['📝 Другой объем']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def remove_keyboard():
    return ReplyKeyboardRemove()
