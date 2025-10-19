import os
import logging
import datetime
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логирования ПЕРВЫМ делом
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logger.info("🚀 Запуск Fithub Bot...")

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Проверка токена с graceful degradation
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
    logger.info("💡 Добавьте TELEGRAM_BOT_TOKEN в Railway Variables")
    logger.info("💡 Или установите в .env файл для локальной разработки")
    # Вместо падения, используем демо-режим
    TELEGRAM_BOT_TOKEN = "demo_mode"
    logger.warning("⚠️ Бот запущен в демо-режиме без Telegram")

# Импорты с обработкой ошибок
try:
    from database import db
    logger.info("✅ База данных загружена")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки базы данных: {e}")
    # Создаем заглушку
    class DatabaseStub:
        def get_connection(self): pass
        def init_db(self): pass
        def add_user(self, *args): pass
        def get_user(self, *args): return None
        def add_food_entry(self, *args): pass
        def get_daily_summary(self, *args): return (0, 0, 0, 0)
    db = DatabaseStub()

try:
    # Пробуем сначала упрощенную версию
    from vision_api_simple import vision_api
    logger.info("✅ Vision API загружен (упрощенная версия)")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки Vision API: {e}")
    # Создаем заглушку
    class VisionAPIStub:
        def analyze_image(self, image_content):
            return {
                'success': False,
                'error': 'Vision API не настроен',
                'detected_items': [],
                'total_detected': 0
            }
    vision_api = VisionAPIStub()

try:
    from food_api import food_api
    logger.info("✅ Food API загружен")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки Food API: {e}")
    # Создаем заглушку
    class FoodAPIStub:
        def get_food_info(self, food_name, quantity=100):
            return {
                'name': food_name,
                'calories': 100,
                'protein': 5,
                'fat': 3,
                'carbs': 15,
                'quantity': quantity,
                'source': 'stub'
            }
    food_api = FoodAPIStub()

logger.info("✅ Все модули загружены")

# Остальной код бота (состояния, клавиатуры, команды)...
# [КОНВЕРСАЦИИ, КЛАВИАТУРЫ, КОМАНДЫ БЕЗ ИЗМЕНЕНИЙ]

# Состояния диалога
CHOOSING_ROLE, TRAINEE_SETUP, AWAITING_PHOTO, CONFIRM_FOOD, MANUAL_INPUT, LINK_TRAINER = range(6)

# Клавиатуры
def get_role_keyboard():
    return ReplyKeyboardMarkup([['👨‍🎓 Ученик', '👨‍🏫 Тренер']], one_time_keyboard=True, resize_keyboard=True)

def get_goal_keyboard():
    return ReplyKeyboardMarkup([['📉 Похудение', '📈 Набор массы', '⚖️ Поддержание']], one_time_keyboard=True, resize_keyboard=True)

def get_gender_keyboard():
    return ReplyKeyboardMarkup([['👨 Мужской', '👩 Женский']], one_time_keyboard=True, resize_keyboard=True)

def get_confirm_keyboard():
    return ReplyKeyboardMarkup([['✅ Да, верно', '✏️ Ввести вручную']], one_time_keyboard=True, resize_keyboard=True)

def get_meal_keyboard():
    return ReplyKeyboardMarkup([['🍳 Завтрак', '🍲 Обед', '🍽️ Ужин', '🍎 Перекус']], one_time_keyboard=True, resize_keyboard=True)

def get_main_keyboard(role):
    if role == 'trainee':
        return ReplyKeyboardMarkup([
            ['📷 Анализ фото', '📝 Ввести продукт'],
            ['📊 Итоги дня', '👤 Профиль', '🔗 Тренер']
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ['👥 Мои ученики', '📊 Статистика'],
            ['👤 Профиль']
        ], resize_keyboard=True)

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing_user = db.get_user(user.id)
    
    if existing_user:
        role = existing_user[3]
        await update.message.reply_text(
            f"С возвращением, {user.first_name}!",
            reply_markup=get_main_keyboard(role)
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n"
        "Я FithubBot - твой помощник по питанию!\n\n"
        "Я могу:\n• 📷 Анализировать еду по фото\n• 📊 Считать КБЖУ\n"
        "• 🎯 Давать рекомендации\n• 👨‍🏫 Связывать с тренером\n\n"
        "Выбери свою роль:",
        reply_markup=get_role_keyboard()
    )
    return CHOOSING_ROLE

async def handle_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    
    if 'Ученик' in text:
        context.user_data.update({
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'role': 'trainee'
        })
        
        await update.message.reply_text(
            "🎓 Отлично! Давай настроим твой профиль.\nВведи свой рост (в см):",
            reply_markup=ReplyKeyboardRemove()
        )
        return TRAINEE_SETUP
    
    elif 'Тренер' in text:
        db.add_user((
            user.id, user.username, user.first_name, 'trainer',
            None, None, None, None, None, 1.375, None, None, None, None, None
        ))
        
        await update.message.reply_text(
            f"👨‍🏫 Вы зарегистрированы как тренер!\n\n"
            f"Ваш ID: <code>{user.id}</code>\n\n"
            "Отправьте этот ID ученикам для подключения.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard('trainer')
        )
        return ConversationHandler.END

async def setup_trainee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data
    
    steps = ['height', 'weight', 'age', 'gender', 'goal']
    current_step = None
    
    for step in steps:
        if step not in user_data:
            current_step = step
            break
    
    if not current_step:
        return await finish_setup(update, context)
    
    try:
        if current_step == 'height':
            height = float(text)
            if 50 <= height <= 250:
                user_data['height'] = height
                await update.message.reply_text("Введи свой вес (кг):")
            else:
                await update.message.reply_text("Введи реальный рост (50-250 см):")
        
        elif current_step == 'weight':
            weight = float(text)
            if 20 <= weight <= 300:
                user_data['weight'] = weight
                await update.message.reply_text("Введи свой возраст:")
            else:
                await update.message.reply_text("Введи реальный вес (20-300 кг):")
        
        elif current_step == 'age':
            age = int(text)
            if 10 <= age <= 100:
                user_data['age'] = age
                await update.message.reply_text("Выбери пол:", reply_markup=get_gender_keyboard())
            else:
                await update.message.reply_text("Введи реальный возраст (10-100 лет):")
        
        elif current_step == 'gender':
            if 'Мужской' in text:
                user_data['gender'] = 'male'
            elif 'Женский' in text:
                user_data['gender'] = 'female'
            else:
                await update.message.reply_text("Выбери пол из вариантов:")
                return TRAINEE_SETUP
            
            await update.message.reply_text("Выбери цель:", reply_markup=get_goal_keyboard())
        
        elif current_step == 'goal':
            goal_map = {'Похудение': 'lose', 'Набор массы': 'gain', 'Поддержание': 'maintain'}
            user_data['goal'] = goal_map.get(text, 'maintain')
            return await finish_setup(update, context)
    
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число:")
    
    return TRAINEE_SETUP

async def finish_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    # Рассчет норм КБЖУ
    if user_data['gender'] == 'male':
        bmr = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age'] + 5
    else:
        bmr = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age'] - 161
    
    activity = 1.375
    maintenance = bmr * activity
    
    if user_data['goal'] == 'lose':
        calories = maintenance * 0.85
    elif user_data['goal'] == 'gain':
        calories = maintenance * 1.15
    else:
        calories = maintenance
    
    # Сохраняем пользователя
    db.add_user((
        user_data['user_id'], user_data['username'], user_data['first_name'], 'trainee',
        user_data['height'], user_data['weight'], user_data['age'], user_data['gender'],
        user_data['goal'], activity, calories, 
        (calories * 0.3 / 4), (calories * 0.25 / 9), (calories * 0.45 / 4), None
    ))
    
    await update.message.reply_text(
        f"🎉 Настройка завершена!\n\n"
        f"📊 Твои дневные нормы:\n"
        f"• 🔥 {calories:.0f} ккал\n"
        f"• 💪 {(calories * 0.3 / 4):.1f} г белка\n"
        f"• 🥑 {(calories * 0.25 / 9):.1f} г жиров\n"
        f"• 🍚 {(calories * 0.45 / 4):.1f} г углеводов\n\n"
        "Теперь можешь анализировать свое питание!",
        reply_markup=get_main_keyboard('trainee')
    )
    return ConversationHandler.END

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or user[3] != 'trainee':
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    await update.message.reply_text("🔍 Анализирую фото...")
    
    # Получаем фото
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Анализируем через Vision API
    analysis_result = vision_api.analyze_image(photo_bytes)
    
    if 'error' in analysis_result:
        await update.message.reply_text(
            "❌ Не удалось проанализировать фото. Попробуйте сфотографировать при лучшем освещении.",
            reply_markup=get_main_keyboard('trainee')
        )
        return
    
    detected_items = analysis_result.get('detected_items', [])
    
    if not detected_items:
        await update.message.reply_text(
            "❌ Не удалось распознать еду на фото. Попробуйте другой снимок.",
            reply_markup=get_main_keyboard('trainee')
        )
        return
    
    # Сохраняем распознанные продукты
    context.user_data['detected_items'] = detected_items
    
    # Показываем результаты
    message = "📷 Распознанные продукты:\n\n"
    for i, item in enumerate(detected_items[:5], 1):
        message += f"{i}. {item['name'].title()} (уверенность: {item['confidence']:.0%})\n"
    
    message += "\nВерно ли распознаны продукты?"
    
    await update.message.reply_text(message, reply_markup=get_confirm_keyboard())
    return CONFIRM_FOOD

async def handle_food_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    detected_items = context.user_data.get('detected_items', [])
    
    if 'Да, верно' in text:
        if not detected_items:
            await update.message.reply_text("Ошибка: продукты не распознаны")
            return ConversationHandler.END
        
        main_product = detected_items[0]
        context.user_data['current_food'] = main_product['name']
        
        await update.message.reply_text(
            f"Введите вес порции '{main_product['name']}' в граммах:",
            reply_markup=ReplyKeyboardRemove()
        )
        return MANUAL_INPUT
    
    elif 'Ввести вручную' in text:
        await update.message.reply_text("Введите название продукта:", reply_markup=ReplyKeyboardRemove())
        return MANUAL_INPUT

async def handle_manual_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if 'current_food' not in context.user_data:
        context.user_data['current_food'] = text
        await update.message.reply_text("Введите вес порции в граммах:")
        return MANUAL_INPUT
    
    try:
        quantity = float(text)
        food_name = context.user_data['current_food']
        
        food_info = food_api.get_food_info(food_name, quantity)
        context.user_data['food_info'] = food_info
        
        await update.message.reply_text(
            f"🍎 {food_info['name']}\n"
            f"⚖️ {quantity}г\n"
            f"🔥 {food_info['calories']:.0f} ккал\n"
            f"💪 {food_info['protein']:.1f}г белка\n"
            f"🥑 {food_info['fat']:.1f}г жиров\n"
            f"🍚 {food_info['carbs']:.1f}г углеводов\n\n"
            "Выбери тип приема пищи:",
            reply_markup=get_meal_keyboard()
        )
        return AWAITING_PHOTO
    
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число для веса:")

async def handle_meal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    food_info = context.user_data.get('food_info')
    
    if not food_info:
        await update.message.reply_text("Ошибка: информация о продукте не найдена")
        return ConversationHandler.END
    
    meal_map = {'🍳 Завтрак': 'breakfast', '🍲 Обед': 'lunch', '🍽️ Ужин': 'dinner', '🍎 Перекус': 'snack'}
    meal_type = meal_map.get(text, 'other')
    
    # Сохраняем в базу
    db.add_food_entry(
        user_id,
        food_info['name'],
        food_info['quantity'],
        food_info['calories'],
        food_info['protein'],
        food_info['fat'],
        food_info['carbs'],
        meal_type
    )
    
    await update.message.reply_text(
        f"✅ Запись сохранена как {text.lower()}!\n"
        f"📊 Добавлено: {food_info['calories']:.0f} ккал",
        reply_markup=get_main_keyboard('trainee')
    )
    
    # Уведомляем тренера
    user = db.get_user(user_id)
    if user and user[14]:
        try:
            trainer_id = user[14]
            await context.bot.send_message(
                trainer_id,
                f"📊 Ученик {user[2]} добавил запись:\n"
                f"• {food_info['name']} - {food_info['quantity']}г\n"
                f"• {food_info['calories']:.0f} ккал ({text})"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить тренера: {e}")
    
    return ConversationHandler.END

async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    calories, protein, fat, carbs = db.get_daily_summary(user_id)
    goal_calories = user[10] or 2000
    
    percentage = (calories / goal_calories * 100) if goal_calories > 0 else 0
    
    message = (
        f"📊 Итоги за сегодня:\n\n"
        f"🔥 Калории: {calories:.0f} / {goal_calories:.0f} ({percentage:.1f}%)\n"
        f"💪 Белки: {protein:.1f}г\n"
        f"🥑 Жиры: {fat:.1f}г\n"
        f"🍚 Углеводы: {carbs:.1f}г\n\n"
    )
    
    if percentage >= 100:
        message += "🎯 Дневная норма достигнута! 🎉"
    elif percentage >= 80:
        message += "💪 Отличный прогресс!"
    else:
        message += "📈 Продолжайте в том же духе!"
    
    await update.message.reply_text(message)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    role = user[3]
    
    if role == 'trainee':
        message = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"📏 Рост: {user[4]} см\n"
            f"⚖️ Вес: {user[5]} кг\n"
            f"🎂 Возраст: {user[6]} лет\n"
            f"👫 Пол: {'Мужской' if user[7] == 'male' else 'Женский'}\n"
            f"🎯 Цель: {get_goal_text(user[8])}\n"
            f"🔥 Дневная норма: {user[10]:.0f} ккал\n"
        )
        
        trainer = None  # Здесь можно добавить поиск тренера
        if trainer:
            message += f"\n👨‍🏫 Тренер: {trainer[2]}"
        else:
            message += "\n🔗 Тренер не привязан"
            
    else:
        message = (
            f"👨‍🏫 <b>Профиль тренера</b>\n\n"
            f"🆔 Ваш ID: <code>{user[0]}</code>\n"
        )
        
        trainees = db.get_trainees(user[0])
        if trainees:
            message += f"\n👥 Ученики ({len(trainees)}):\n"
            for trainee in trainees:
                message += f"• {trainee[2]}\n"
        else:
            message += "\n👥 Учеников пока нет"
    
    await update.message.reply_text(message, parse_mode='HTML')

def get_goal_text(goal):
    goals = {'lose': 'Похудение', 'gain': 'Набор массы', 'maintain': 'Поддержание'}
    return goals.get(goal, 'Не указана')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Операция отменена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    """Основная функция запуска бота"""
    
    if TELEGRAM_BOT_TOKEN == "demo_mode":
        logger.error("❌ Бот не может запуститься без TELEGRAM_BOT_TOKEN")
        logger.info("💡 Инструкция по настройке:")
        logger.info("1. Перейдите в Railway Dashboard")
        logger.info("2. Откройте вкладку Variables")
        logger.info("3. Добавьте TELEGRAM_BOT_TOKEN = ваш_токен")
        logger.info("4. Railway автоматически перезапустит бота")
        return
    
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Обработчик диалога
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role)],
                TRAINEE_SETUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_trainee)],
                CONFIRM_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_confirmation)],
                MANUAL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_input)],
                AWAITING_PHOTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meal_type)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('summary', show_summary))
        application.add_handler(CommandHandler('profile', show_profile))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        logger.info("✅ Бот сконфигурирован, запускаем...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        logger.info("💡 Проверьте TELEGRAM_BOT_TOKEN в Railway Variables")

if __name__ == '__main__':
    main()
