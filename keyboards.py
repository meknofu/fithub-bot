from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

def get_user_type_keyboard():
    keyboard = [
        ['I am a Trainer', 'I am a Trainee']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_confirm_keyboard():
    keyboard = [
        ['✅ Yes, all correct', '❌ No, correct manually']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_meal_type_keyboard():
    keyboard = [
        ['Breakfast', 'Lunch'],
        ['Snack', 'Dinner']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_yes_no_keyboard():
    keyboard = [
        ['✅ Yes', '❌ No']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_drink_method_keyboard():
    keyboard = [
        ['Enter Drink Name']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_drink_categories_keyboard():
    keyboard = [
        ['Water', 'Soda', 'Coffee/Tea'],
        ['Juice', 'Dairy Drink', 'Alcohol'],
        ['Energy Drink', 'Sports Drink', 'Other']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_popular_drinks_keyboard():
    keyboard = [
        ['Water', 'Cola', 'Coffee'],
        ['Orange Juice', 'Milk', 'Beer'],
        ['Red Bull', 'Isotonic', 'Other Drink']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_drink_volumes_keyboard():
    keyboard = [
        ['250ml (glass)', '330ml (can)'],
        ['500ml (bottle)', '1000ml (liter)'],
        ['Other Volume']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_reference_object_keyboard():
    keyboard = [
        ['Fork', 'Spoon', 'Phone'],
        ['Card', 'Palm', 'No Reference']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def remove_keyboard():
    return ReplyKeyboardRemove()
