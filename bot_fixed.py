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

logger.info("🚀 Инициализация Fithub Bot...")

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

# Проверка токена
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

# Импорт модулей
try:
    from database import db
    from usda_database import usda_db
    from nutrition_calculator import nutrition_calc
    from vision_analyzer import vision_analyzer
    logger.info("✅ Все модули загружены")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки модулей: {e}")
    raise

# Состояния диалога
(
    CHOOSING_ROLE, TRAINEE_SETUP, TRAINEE_GOAL, TRAINEE_ACTIVITY,
    AWAITING_PHOTO, CONFIRM_FOOD, MEAL_TYPE_SELECTION,
    LINK_TRAINER, MANUAL_FOOD_INPUT, FOOD_QUANTITY
) = range(10)

# [ВАШ СУЩЕСТВУЮЩИЙ КОД КЛАВИАТУР И ФУНКЦИЙ...]
# ВСТАВЬТЕ СЮДА ВЕСЬ ВАШ СУЩЕСТВУЮЩИЙ КОД ИЗ bot.py
# НАЧИНАЯ С get_role_keyboard() ДО КОНЦА

def main():
    """Основная функция с защитой от конфликтов"""
    logger.info("🔄 Создаем Application...")
    
    # Создаем Application с настройками для Railway
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # [ВАША СУЩЕСТВУЮЩАЯ КОНФИГУРАЦИЯ ОБРАБОТЧИКОВ...]
    # ВСТАВЬТЕ СЮДА ВСЮ КОНФИГУРАЦИЮ ОБРАБОТЧИКОВ ИЗ ВАШЕГО КОДА
    
    logger.info("✅ Бот сконфигурирован, запускаем...")
    
    try:
        # Запускаем с настройками для предотвращения конфликтов
        application.run_polling(
            drop_pending_updates=True,  # Игнорируем старые сообщения
            allowed_updates=['message', 'callback_query'],
            close_loop=False
        )
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        # На Railway приложение автоматически перезапустится

if __name__ == '__main__':
    main()
