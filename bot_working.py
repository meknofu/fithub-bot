import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import sqlite3
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Состояния разговора
CHOOSING_ROLE, ENTERING_HEIGHT, ENTERING_WEIGHT, ENTERING_AGE, CONFIRMING_DATA = range(5)

# Клавиатура для выбора роли
role_keyboard = [['👨‍🎓 Ученик', '👨‍🏫 Учитель']]
role_markup = ReplyKeyboardMarkup(role_keyboard, one_time_keyboard=True, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает разговор и спрашивает о роли."""
    user = update.message.from_user
    logger.info(f"✅ Получена команда /start от пользователя {user.id}")
    
    await update.message.reply_text(
        "👋 Добро пожаловать! Я бот для анализа физического состояния.\n\n"
        "🤔 Кто вы?",
        reply_markup=role_markup
    )
    return CHOOSING_ROLE

async def role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет выбор роли и запрашивает рост."""
    user = update.message.from_user
    role = update.message.text
    logger.info(f"✅ Пользователь {user.id} выбрал: {role}")
    
    context.user_data['role'] = role
    
    await update.message.reply_text(
        "📏 Пожалуйста, введите ваш рост в сантиметрах:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ENTERING_HEIGHT

async def height_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет рост и запрашивает вес."""
    user = update.message.from_user
    height_text = update.message.text
    
    # Валидация роста
    try:
        height = int(height_text)
        if height < 50 or height > 250:
            await update.message.reply_text("❌ Рост должен быть от 50 до 250 см. Пожалуйста, введите корректный рост:")
            return ENTERING_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите рост цифрами (например, 175):")
        return ENTERING_HEIGHT
    
    logger.info(f"✅ Пользователь {user.id} ввел рост: {height}")
    context.user_data['height'] = height
    
    await update.message.reply_text("⚖️ Теперь введите ваш вес в килограммах:")
    return ENTERING_WEIGHT

async def weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет вес и запрашивает возраст."""
    user = update.message.from_user
    weight_text = update.message.text
    
    # Валидация веса
    try:
        weight = float(weight_text)
        if weight < 10 or weight > 300:
            await update.message.reply_text("❌ Вес должен быть от 10 до 300 кг. Пожалуйста, введите корректный вес:")
            return ENTERING_WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите вес цифрами (например, 65.5):")
        return ENTERING_WEIGHT
    
    logger.info(f"✅ Пользователь {user.id} ввел вес: {weight}")
    context.user_data['weight'] = weight
    
    await update.message.reply_text("🎂 Введите ваш возраст:")
    return ENTERING_AGE

async def age_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет возраст и показывает сводку."""
    user = update.message.from_user
    age_text = update.message.text
    
    # Валидация возраста
    try:
        age = int(age_text)
        if age < 1 or age > 120:
            await update.message.reply_text("❌ Возраст должен быть от 1 до 120 лет. Пожалуйста, введите корректный возраст:")
            return ENTERING_AGE
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите возраст цифрами (например, 25):")
        return ENTERING_AGE
    
    logger.info(f"✅ Пользователь {user.id} ввел возраст: {age}")
    context.user_data['age'] = age
    
    # Показываем сводку данных
    role = context.user_data.get('role', 'Не указано')
    height = context.user_data.get('height', 'Не указано')
    weight = context.user_data.get('weight', 'Не указано')
    
    summary = (
        "📊 **Сводка данных:**\n\n"
        f"👤 **Роль:** {role}\n"
        f"📏 **Рост:** {height} см\n"
        f"⚖️ **Вес:** {weight} кг\n"
        f"🎂 **Возраст:** {age} лет\n\n"
        "✅ Все данные корректны?"
    )
    
    # Клавиатура для подтверждения
    confirm_keyboard = [['✅ Да', '❌ Нет']]
    confirm_markup = ReplyKeyboardMarkup(confirm_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(summary, reply_markup=confirm_markup, parse_mode='Markdown')
    return CONFIRMING_DATA

async def data_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает подтверждение данных и завершает разговор."""
    user = update.message.from_user
    confirmation = update.message.text
    
    if confirmation == '✅ Да':
        # Сохраняем данные в базу
        save_user_data(user.id, context.user_data)
        
        # Рассчитываем ИМТ
        height = context.user_data.get('height')
        weight = context.user_data.get('weight')
        
        if height and weight:
            height_m = height / 100
            bmi = weight / (height_m * height_m)
            
            # Определяем категорию ИМТ
            if bmi < 18.5:
                category = "недостаточный вес"
            elif bmi < 25:
                category = "нормальный вес"
            elif bmi < 30:
                category = "избыточный вес"
            else:
                category = "ожирение"
            
            response = (
                "🎉 **Данные сохранены!**\n\n"
                f"📊 **Ваш ИМТ:** {bmi:.1f}\n"
                f"📈 **Категория:** {category}\n\n"
                "Спасибо за использование бота! 👋"
            )
        else:
            response = "🎉 Данные сохранены! Спасибо за использование бота! 👋"
        
        await update.message.reply_text(response, reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        
    else:
        await update.message.reply_text(
            "🔄 Давайте начнем заново. Выберите вашу роль:",
            reply_markup=role_markup
        )
        return CHOOSING_ROLE
    
    # Очищаем данные пользователя
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет и завершает разговор."""
    user = update.message.from_user
    logger.info(f"❌ Пользователь {user.id} отменил разговор.")
    await update.message.reply_text(
        "👋 До свидания! Если захотите начать заново, отправьте /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def save_user_data(user_id, user_data):
    """Сохраняет данные пользователя в базу данных."""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Создаем таблицу если ее нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT,
                height INTEGER,
                weight REAL,
                age INTEGER,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Сохраняем данные
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, role, height, weight, age, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data.get('role'),
            user_data.get('height'),
            user_data.get('weight'),
            user_data.get('age'),
            json.dumps(user_data)
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Данные пользователя {user_id} сохранены в базу")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении данных: {e}")

def main() -> None:
    """Запускает бота."""
    # Создаем Application
    application = Application.builder().token("8178401200:AAEh5oeYRhgBJ8UrF1s2rlZtF0SuI1hPOAM").build()

    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ROLE: [
                MessageHandler(filters.Regex('^(👨‍🎓 Ученик|👨‍🏫 Учитель)$'), role_choice)
            ],
            ENTERING_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, height_received)
            ],
            ENTERING_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, weight_received)
            ],
            ENTERING_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, age_received)
            ],
            CONFIRMING_DATA: [
                MessageHandler(filters.Regex('^(✅ Да|❌ Нет)$'), data_confirmed)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()
    logger.info("🤖 Бот запущен")

if __name__ == '__main__':
    main()
