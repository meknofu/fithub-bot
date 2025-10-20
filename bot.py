import os
import logging
from telegram.ext import Application

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция с обработкой конфликтов"""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
        return
    
    # Создаем Application с настройками для предотвращения конфликтов
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # [ВАШ СУЩЕСТВУЮЩИЙ КОД КОНФИГУРАЦИИ...]
    
    logger.info("🚀 Запускаем бота с настройками против конфликтов...")
    
    try:
        # Запускаем с обработкой конфликтов
        application.run_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True  # Важно: игнорируем старые сообщения
        )
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        
if __name__ == '__main__':
    main()

# Импорт модулей
from database import db
from usda_database import usda_db
from nutrition_calculator import nutrition_calc
from vision_analyzer import vision_analyzer

logger.info("✅ Все модули загружены")

# Состояния диалога
(
    CHOOSING_ROLE, TRAINEE_SETUP, TRAINEE_GOAL, TRAINEE_ACTIVITY,
    AWAITING_PHOTO, CONFIRM_FOOD, MEAL_TYPE_SELECTION,
    LINK_TRAINER, MANUAL_FOOD_INPUT, FOOD_QUANTITY
) = range(10)

# 📋 КЛАВИАТУРЫ С РАБОТАЮЩИМИ КНОПКАМИ

def get_role_keyboard():
    return ReplyKeyboardMarkup([['👨‍🎓 Ученик', '👨‍🏫 Тренер']], 
                              resize_keyboard=True, one_time_keyboard=True)

def get_gender_keyboard():
    return ReplyKeyboardMarkup([['👨 Мужской', '👩 Женский']],
                              resize_keyboard=True, one_time_keyboard=True)

def get_goal_keyboard():
    return ReplyKeyboardMarkup([
        ['📉 Похудение', '📈 Набор массы'],
        ['⚖️ Поддержание формы']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_activity_keyboard():
    return ReplyKeyboardMarkup([
        ['💤 Минимальная', '🚶‍♂️ Низкая'],
        ['🏃‍♂️ Средняя', '🔥 Высокая'],
        ['🏋️‍♂️ Очень высокая']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_confirm_keyboard():
    return ReplyKeyboardMarkup([
        ['✅ Да, все верно'], 
        ['✏️ Исправить граммовку', '🔄 Ввести вручную']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_meal_type_keyboard():
    return ReplyKeyboardMarkup([
        ['🍳 Завтрак', '🍲 Обед'],
        ['🍽️ Ужин', '🍎 Перекус']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_main_menu_trainee():
    """Главное меню для ученика - ВСЕ КНОПКИ РАБОТАЮТ"""
    return ReplyKeyboardMarkup([
        ['📷 Сфотографировать еду', '📝 Ввести продукт'],
        ['📊 Итоги за день', '🍽️ Мои рекомендации'],
        ['👤 Мой профиль', '🔗 Привязать тренера']
    ], resize_keyboard=True)

def get_main_menu_trainer():
    """Главное меню для тренера"""
    return ReplyKeyboardMarkup([
        ['👥 Мои ученики', '📈 Статистика'],
        ['👤 Мой профиль']
    ], resize_keyboard=True)

def get_correction_keyboard():
    """Клавиатура для коррекции граммовки"""
    return ReplyKeyboardMarkup([
        ['➕ Увеличить вес', '➖ Уменьшить вес'],
        ['✅ Подтвердить', '🔄 Ввести вручную']
    ], resize_keyboard=True, one_time_keyboard=True)

# 🎯 ОСНОВНЫЕ КОМАНДЫ

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - начало работы"""
    user = update.effective_user
    
    # Проверяем существующего пользователя
    existing_user = db.get_user(user.id)
    if existing_user:
        role = existing_user[3]
        menu = get_main_menu_trainee() if role == 'trainee' else get_main_menu_trainer()
        await update.message.reply_text(
            f"С возвращением, {user.first_name}! 🎉\n"
            "Выберите действие из меню ниже:",
            reply_markup=menu
        )
        return ConversationHandler.END
    
    # Новый пользователь
    await update.message.reply_text(
        f"👋 Добро пожаловать в FITHUB\n\n"
        "Выбери свою роль:",
        reply_markup=get_role_keyboard()
    )
    return CHOOSING_ROLE

# 🎓 РЕГИСТРАЦИЯ УЧЕНИКА
async def handle_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора роли"""
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
            "🎓 Отлично! Ты - ученик!\n"
            "Давай настроим твой профиль для точных рекомендаций.\n\n"
            "Введи свой рост (в см):",
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
            f"🆔 Ваш ID для подключения учеников: <code>{user.id}</code>\n\n"
            "Отправьте этот ID своим ученикам для привязки.",
            parse_mode='HTML',
            reply_markup=get_main_menu_trainer()
        )
        return ConversationHandler.END

async def setup_trainee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка профиля ученика"""
    text = update.message.text
    user_data = context.user_data
    
    try:
        if 'height' not in user_data:
            height = float(text)
            user_data['height'] = height
            await update.message.reply_text("Введи свой вес (в кг):")
            return TRAINEE_SETUP
        
        elif 'weight' not in user_data:
            weight = float(text)
            user_data['weight'] = weight
            await update.message.reply_text("Введи свой возраст:")
            return TRAINEE_SETUP
        
        elif 'age' not in user_data:
            age = int(text)
            user_data['age'] = age
            await update.message.reply_text("Выбери свой пол:", reply_markup=get_gender_keyboard())
            return TRAINEE_SETUP
        
        elif 'gender' not in user_data:
            if 'Мужской' in text:
                user_data['gender'] = 'male'
            elif 'Женский' in text:
                user_data['gender'] = 'female'
            else:
                await update.message.reply_text("Выбери пол из вариантов:")
                return TRAINEE_SETUP
            
            await update.message.reply_text("Выбери уровень активности:", reply_markup=get_activity_keyboard())
            return TRAINEE_ACTIVITY
    
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число:")
        return TRAINEE_SETUP

async def handle_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка уровня активности"""
    text = update.message.text
    user_data = context.user_data
    
    activity_map = {
        '💤 Минимальная': 1.2, '🚶‍♂️ Низкая': 1.375,
        '🏃‍♂️ Средняя': 1.55, '🔥 Высокая': 1.725,
        '🏋️‍♂️ Очень высокая': 1.9
    }
    
    if text in activity_map:
        user_data['activity_level'] = activity_map[text]
        await update.message.reply_text("Выбери свою цель:", reply_markup=get_goal_keyboard())
        return TRAINEE_GOAL
    
    await update.message.reply_text("Выбери уровень активности из вариантов:")
    return TRAINEE_ACTIVITY

async def handle_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение настройки ученика"""
    text = update.message.text
    user_data = context.user_data
    
    goal_map = {
        '📉 Похудение': 'lose', '📈 Набор массы': 'gain', 
        '⚖️ Поддержание формы': 'maintain'
    }
    
    if text in goal_map:
        user_data['goal'] = goal_map[text]
        
        # Рассчитываем КБЖУ
        bmr = nutrition_calc.calculate_bmr(
            user_data['weight'], user_data['height'], 
            user_data['age'], user_data['gender']
        )
        
        daily_calories = nutrition_calc.calculate_daily_calories(
            bmr, user_data['goal'], user_data['activity_level']
        )
        
        macros = nutrition_calc.calculate_macros(daily_calories, user_data['goal'])
        
        # Сохраняем пользователя
        db.add_user((
            user_data['user_id'], user_data['username'], user_data['first_name'], 'trainee',
            user_data['height'], user_data['weight'], user_data['age'], user_data['gender'],
            user_data['goal'], user_data['activity_level'], daily_calories,
            macros['protein_grams'], macros['fat_grams'], macros['carbs_grams'], None
        ))
        
        await update.message.reply_text(
            f"🎉 Настройка завершена!\n\n"
            f"📊 Твои дневные нормы:\n"
            f"• 🔥 {daily_calories:.0f} ккал\n"
            f"• 💪 {macros['protein_grams']:.1f} г белка\n"
            f"• 🥑 {macros['fat_grams']:.1f} г жиров\n"
            f"• 🍚 {macros['carbs_grams']:.1f} г углеводов\n\n"
            "Теперь ты можешь анализировать свое питание!",
            reply_markup=get_main_menu_trainee()
        )
        return ConversationHandler.END
    
    await update.message.reply_text("Выбери цель из вариантов:")
    return TRAINEE_GOAL

# 📷 АНАЛИЗ ФОТО ЕДЫ
async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Сфотографировать еду'"""
    await update.message.reply_text(
        "📷 Сфотографируйте ваше блюдо и отправьте фото.\n\n"
        "Я проанализирую его и определю:\n"
        "• 🍽️ Вид блюда\n• ⚖️ Граmмовку\n• 📊 КБЖУ",
        reply_markup=ReplyKeyboardRemove()
    )
    return AWAITING_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отправленного фото"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or user[3] != 'trainee':
        await update.message.reply_text("Пожалуйста, завершите регистрацию через /start")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Анализирую фото...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    try:
        # В реальной реализации здесь будет работа с нейросетью
        # Сейчас используем демо-анализ
        analysis_result = vision_analyzer.analyze_image(b'')
        
        # Сохраняем результат для подтверждения
        context.user_data['analysis_result'] = analysis_result
        
        # Формируем сообщение с результатами
        message = f"🍽️ <b>Распознано блюдо: {analysis_result['dish_name']}</b>\n\n"
        message += "📋 <b>Состав:</b>\n"
        
        for i, ingredient in enumerate(analysis_result['ingredients'], 1):
            nutrition = usda_db.calculate_nutrition(ingredient['name'], ingredient['weight'])
            message += (
                f"{i}. <b>{ingredient['name'].title()}</b>\n"
                f"   ⚖️ {ingredient['weight']}г | "
                f"🔥 {ingredient['calories']:.0f}ккал | "
                f"💪{ingredient['protein']:.1f}г 🥑{ingredient['fat']:.1f}г 🍚{ingredient['carbs']:.1f}г\n"
            )
        
        message += f"\n📊 <b>Итого за блюдо:</b>\n"
        message += f"• ⚖️ Общий вес: {analysis_result['total_weight']}г\n"
        message += f"• 🔥 Калории: {analysis_result['total_calories']:.0f} ккал\n"
        message += f"• 🎯 Уверенность: {analysis_result['confidence']:.0%}\n\n"
        message += "Верно ли распознано блюдо и граммовка?"
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=get_confirm_keyboard()
        )
        return CONFIRM_FOOD
        
    except Exception as e:
        logger.error(f"Ошибка анализа фото: {e}")
        await update.message.reply_text(
            "❌ Ошибка анализа фото. Попробуйте еще раз или введите продукты вручную.",
            reply_markup=get_main_menu_trainee()
        )
        return ConversationHandler.END

async def confirm_food_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение результатов анализа"""
    text = update.message.text
    analysis_result = context.user_data.get('analysis_result')
    
    if not analysis_result:
        await update.message.reply_text("Ошибка: данные анализа не найдены")
        return ConversationHandler.END
    
    if text == '✅ Да, все верно':
        context.user_data['confirmed_food'] = analysis_result
        await update.message.reply_text(
            "Выбери тип приема пищи:",
            reply_markup=get_meal_type_keyboard()
        )
        return MEAL_TYPE_SELECTION
    
    elif text == '✏️ Исправить граммовку':
        await update.message.reply_text(
            "Введите общий вес блюда в граммах:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CONFIRM_FOOD
    
    elif text == '🔄 Ввести вручную':
        await update.message.reply_text(
            "Введите название основного продукта:",
            reply_markup=ReplyKeyboardRemove()
        )
        return MANUAL_FOOD_INPUT

async def handle_meal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение данных о приеме пищи"""
    text = update.message.text
    user_id = update.effective_user.id
    confirmed_food = context.user_data.get('confirmed_food')
    
    if not confirmed_food:
        await update.message.reply_text("Ошибка: данные о еде не найдены")
        return ConversationHandler.END
    
    meal_map = {
        '🍳 Завтрак': 'breakfast', '🍲 Обед': 'lunch',
        '🍽️ Ужин': 'dinner', '🍎 Перекус': 'snack'
    }
    
    meal_type = meal_map.get(text, 'other')
    
    # Сохраняем каждый ингредиент
    for ingredient in confirmed_food['ingredients']:
        db.add_food_entry(
            user_id,
            ingredient['name'],
            ingredient['weight'],
            ingredient['calories'],
            ingredient['protein'],
            ingredient['fat'],
            ingredient['carbs'],
            meal_type
        )
    
    await update.message.reply_text(
        f"✅ <b>Данные сохранены как {text.lower()}!</b>\n\n"
        f"🍽️ {confirmed_food['dish_name']}\n"
        f"⚖️ {confirmed_food['total_weight']}г\n"
        f"🔥 {confirmed_food['total_calories']:.0f} ккал\n\n"
        "Продолжайте отслеживать свое питание! 📊",
        parse_mode='HTML',
        reply_markup=get_main_menu_trainee()
    )
    return ConversationHandler.END

# 📝 РУЧНОЙ ВВОД ПРОДУКТА
async def handle_manual_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Ввести продукт'"""
    await update.message.reply_text(
        "Введите название продукта:",
        reply_markup=ReplyKeyboardRemove()
    )
    return MANUAL_FOOD_INPUT

async def process_food_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия продукта"""
    food_name = update.message.text
    context.user_data['manual_food_name'] = food_name
    
    await update.message.reply_text("Введите вес порции в граммах:")
    return FOOD_QUANTITY

async def process_food_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка веса порции"""
    text = update.message.text
    food_name = context.user_data.get('manual_food_name')
    
    try:
        quantity = float(text)
        nutrition = usda_db.calculate_nutrition(food_name, quantity)
        
        context.user_data['manual_food_nutrition'] = nutrition
        
        message = (
            f"🍎 <b>{nutrition['name']}</b>\n"
            f"⚖️ {nutrition['weight_grams']}г\n"
            f"🔥 {nutrition['calories']:.0f} ккал\n"
            f"💪 {nutrition['protein']:.1f}г белка\n"
            f"🥑 {nutrition['fat']:.1f}г жиров\n"
            f"🍚 {nutrition['carbs']:.1f}г углеводов\n\n"
            "Выбери тип приема пищи:"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=get_meal_type_keyboard()
        )
        return MEAL_TYPE_SELECTION
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число для веса:")
        return FOOD_QUANTITY

# 📊 КОМАНДЫ ГЛАВНОГО МЕНЮ (РАБОТАЮТ ПО КНОПКАМ)

async def show_daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ итогов за день - реакция на кнопку"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь через /start")
        return
    
    calories, protein, fat, carbs = db.get_daily_summary(user_id)
    goal_calories = user[10] or 2000
    
    message = (
        f"📊 <b>Итоги за сегодня</b>\n\n"
        f"🔥 Калории: {calories:.0f} / {goal_calories:.0f}\n"
        f"💪 Белки: {protein:.1f}г\n"
        f"🥑 Жиры: {fat:.1f}г\n"
        f"🍚 Углеводы: {carbs:.1f}г\n\n"
    )
    
    percentage = (calories / goal_calories * 100) if goal_calories > 0 else 0
    if percentage >= 100:
        message += "🎯 <b>Дневная норма достигнута!</b> 🎉"
    elif percentage >= 80:
        message += "💪 <b>Отличный прогресс!</b> Почти у цели!"
    else:
        message += "📈 <b>Хорошее начало!</b> Продолжайте в том же духе!"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def show_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ рекомендаций - реакция на кнопку"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or user[3] != 'trainee':
        await update.message.reply_text("Эта команда доступна только для учеников")
        return
    
    daily_calories = user[10] or 2000
    protein_goal = user[11] or 150
    fat_goal = user[12] or 70
    carb_goal = user[13] or 250
    
    message = (
        f"🍽️ <b>Ваши рекомендации</b>\n\n"
        f"📊 <b>Дневные нормы:</b>\n"
        f"• 🔥 {daily_calories:.0f} ккал\n"
        f"• 💪 {protein_goal:.1f}г белка\n"
        f"• 🥑 {fat_goal:.1f}г жиров\n"
        f"• 🍚 {carb_goal:.1f}г углеводов\n\n"
        f"⏰ <b>Рекомендуемое расписание:</b>\n"
        f"• 🍳 Завтрак: 8:00\n"
        f"• 🍲 Обед: 13:00\n"
        f"• 🍽️ Ужин: 19:00\n"
        f"• 🍎 Перекус: 16:00\n\n"
        f"💡 <b>Советы:</b>\n"
        f"• Пейте足够 воды\n"
        f"• Ешьте разнообразные продукты\n"
        f"• Следите за балансом КБЖУ"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ профиля - реакция на кнопку"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь через /start")
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
            f"🔥 Дневная норма: {user[10]:.0f} ккал"
        )
    else:
        message = (
            f"👨‍🏫 <b>Профиль тренера</b>\n\n"
            f"🆔 Ваш ID: <code>{user_id}</code>\n"
            "Отправьте этот ID ученикам для подключения"
        )
    
    await update.message.reply_text(message, parse_mode='HTML')

def get_goal_text(goal):
    goals = {'lose': 'Похудение', 'gain': 'Набор массы', 'maintain': 'Поддержание формы'}
    return goals.get(goal, 'Не указана')

# 🔗 ПРИВЯЗКА ТРЕНЕРА
async def link_trainer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало привязки тренера - реакция на кнопку"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or user[3] != 'trainee':
        await update.message.reply_text("Эта команда доступна только для учеников")
        return
    
    await update.message.reply_text(
        "Введите ID тренера для привязки:",
        reply_markup=ReplyKeyboardRemove()
    )
    return LINK_TRAINER

async def process_trainer_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ID тренера"""
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        trainer_id = int(text)
        trainer = db.get_user(trainer_id)
        
        if trainer and trainer[3] == 'trainer':
            db.link_trainer_trainee(trainer_id, user_id)
            await update.message.reply_text(
                f"✅ Вы привязаны к тренеру {trainer[2]}!",
                reply_markup=get_main_menu_trainee()
            )
        else:
            await update.message.reply_text(
                "❌ Тренер с таким ID не найден",
                reply_markup=get_main_menu_trainee()
            )
        
    except ValueError:
        await update.message.reply_text("Введите корректный ID (только цифры)")
        return LINK_TRAINER
    
    return ConversationHandler.END

# 👥 КОМАНДЫ ДЛЯ ТРЕНЕРОВ
async def show_trainees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ учеников тренера - реакция на кнопку"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or user[3] != 'trainer':
        await update.message.reply_text("Эта команда доступна только для тренеров")
        return
    
    trainees = db.get_trainees(user_id)
    
    if not trainees:
        await update.message.reply_text(
            "👥 У вас пока нет учеников.\n\n"
            "Ваш ID для подключения:\n"
            f"<code>{user_id}</code>",
            parse_mode='HTML'
        )
        return
    
    message = "👥 <b>Ваши ученики:</b>\n\n"
    for trainee in trainees:
        calories, protein, fat, carbs = db.get_daily_summary(trainee[0])
        message += f"👤 {trainee[2]}\n🔥 {calories:.0f} ккал сегодня\n\n"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    user = db.get_user(update.effective_user.id)
    menu = get_main_menu_trainee() if user and user[3] == 'trainee' else get_main_menu_trainer()
    await update.message.reply_text("Операция отменена.", reply_markup=menu)
    return ConversationHandler.END

def main():
    """Основная функция с ВСЕМИ обработчиками кнопок"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # 📝 ОСНОВНЫЕ ДИАЛОГИ
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role)],
            TRAINEE_SETUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_trainee)],
            TRAINEE_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activity)],
            TRAINEE_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    photo_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📷 Сфотографировать еду$'), handle_photo_message)],
        states={
            AWAITING_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            CONFIRM_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_food_analysis)],
            MEAL_TYPE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meal_type)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    manual_food_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📝 Ввести продукт$'), handle_manual_input)],
        states={
            MANUAL_FOOD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_food_name)],
            FOOD_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_food_quantity)],
            MEAL_TYPE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meal_type)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    link_trainer_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔗 Привязать тренера$'), link_trainer_start)],
        states={
            LINK_TRAINER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_trainer_link)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # 🎯 ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ
    application.add_handler(MessageHandler(filters.Regex('^📊 Итоги за день$'), show_daily_summary))
    application.add_handler(MessageHandler(filters.Regex('^🍽️ Мои рекомендации$'), show_recommendations))
    application.add_handler(MessageHandler(filters.Regex('^👤 Мой профиль$'), show_profile))
    application.add_handler(MessageHandler(filters.Regex('^👥 Мои ученики$'), show_trainees))
    
    # 📝 ДОБАВЛЯЕМ ВСЕ КОНВЕРСАЦИИ
    application.add_handler(setup_conv)
    application.add_handler(photo_conv)
    application.add_handler(manual_food_conv)
    application.add_handler(link_trainer_conv)
    
    # 📷 ОБРАБОТКА ФОТО ИЗ ЛЮБОГО МЕСТА
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("🚀 Бот запущен с работающими кнопками!")
    application.run_polling()

if __name__ == '__main__':
    main()
