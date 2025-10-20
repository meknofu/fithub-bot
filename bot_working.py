import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
CHOOSING_ROLE, TRAINEE_SETUP = range(2)

def get_role_keyboard():
    return ReplyKeyboardMarkup([['👨‍🎓 Ученик', '👨‍🏫 Тренер']], 
                              resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - ДОЛЖНА РАБОТАТЬ"""
    user = update.effective_user
    logger.info(f"✅ Получена команда /start от пользователя {user.id}")
    
    await update.message.reply_text(
        f"👋 Добро пожаловать в FITHUB!\n\n"
        "Выбери свою роль:",
        reply_markup=get_role_keyboard()
    )
    return CHOOSING_ROLE

async def handle_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора роли"""
    text = update.message.text
    user = update.effective_user
    logger.info(f"✅ Пользователь {user.id} выбрал: {text}")
    
    if 'Ученик' in text:
        await update.message.reply_text(
            "🎓 Отлично! Ты - ученик!\n"
            "Введи свой рост (в см):",
            reply_markup=None
        )
        return TRAINEE_SETUP
    
    elif 'Тренер' in text:
        await update.message.reply_text(
            f"👨‍🏫 Вы зарегистрированы как тренер!\n"
            f"Ваш ID: <code>{user.id}</code>",
            parse_mode='HTML'
        )
        return ConversationHandler.END

async def handle_trainee_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода роста"""
    text = update.message.text
    user = update.effective_user
    logger.info(f"✅ Пользователь {user.id} ввел рост: {text}")
    
    try:
        height = float(text)
        await update.message.reply_text(
            f"📏 Рост: {height} см\n"
            "Теперь введи свой вес (в кг):"
        )
        return TRAINEE_SETUP
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число для роста:")
        return TRAINEE_SETUP

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"❌ Ошибка: {context.error}")

def main():
    """Основная функция - ПРОСТАЯ И РАБОЧАЯ"""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
        return
    
    logger.info("🚀 Создаем Application...")
    
    # Создаем Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ROLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role)
            ],
            TRAINEE_SETUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trainee_setup)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    logger.info("✅ Бот сконфигурирован, запускаем...")
    
    # Запускаем бота
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query']
    )

if __name__ == '__main__':
    main()
