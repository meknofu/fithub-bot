import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from config import Config
from database import db
from vision_api import VisionAPI
from kbju_calculator import KBJUCalculator
from user_manager import UserManager
from keyboards import *
import io
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class FithubBot:
    def __init__(self):
        self.db = db
        self.vision = VisionAPI()
        self.calculator = KBJUCalculator()
        self.user_manager = UserManager()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        await update.message.reply_html(
            f"👋 Добро пожаловать в FITHUB!\n\n"
            f"Пожалуйста, выберите вашу роль",
            reply_markup=get_user_type_keyboard()
        )
        
        self.user_manager.set_user_state(user.id, 'awaiting_user_type')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message_text = update.message.text
        state = self.user_manager.get_user_state(user_id)
        
        if state == 'awaiting_user_type':
            await self.handle_user_type(update, context)
        elif state == 'awaiting_height':
            await self.handle_height(update, context)
        elif state == 'awaiting_weight':
            await self.handle_weight(update, context)
        elif state == 'awaiting_trainer_id':
            await self.handle_trainer_id(update, context)
        elif state == 'awaiting_manual_weight':
            await self.handle_manual_weight(update, context)
        elif state == 'awaiting_food_name':
            await self.handle_food_name(update, context)

    async def handle_user_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message_text = update.message.text
        
        if 'тренер' in message_text.lower():
            user_type = 'trainer'
            self.db.add_user({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name,
                'user_type': user_type
            })
            
            await update.message.reply_text(
                "Отлично! Вы зарегистрированы как тренер. 🏋️\n\n"
                "Теперь вы можете:\n"
                "• Добавлять учеников\n"
                "• Просматривать их рацион\n"
                "• Получать отчеты о питании\n\n"
                "Для добавления ученика попросите его отправить вам свой ID:",
                reply_markup=remove_keyboard()
            )
            
        elif 'ученик' in message_text.lower():
            user_type = 'trainee'
            self.db.add_user({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name,
                'user_type': user_type
            })
            
            await update.message.reply_text(
                "Отлично! Вы зарегистрированы как ученик. 🧑‍🎓\n\n"
                "Для расчета вашей нормы КБЖУ мне нужны некоторые данные:\n\n"
                "Введите ваш рост в см:",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_height')
            
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите вариант из клавиатуры:",
                reply_markup=get_user_type_keyboard()
            )

    async def handle_height(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            height = float(update.message.text)
            if height < 100 or height > 250:
                await update.message.reply_text("Пожалуйста, введите корректный рост (100-250 см):")
                return
                
            self.user_manager.set_user_state(user_id, 'awaiting_weight', {'height': height})
            await update.message.reply_text("Теперь введите ваш вес в кг:")
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")

    async def handle_weight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            weight = float(update.message.text)
            if weight < 30 or weight > 300:
                await update.message.reply_text("Пожалуйста, введите корректный вес (30-300 кг):")
                return
                
            user_data = self.user_manager.get_user_data(user_id)
            height = user_data['height']
            
            # Рассчитываем КБЖУ (упрощенная версия)
            kbju = self.calculator.calculate_daily_kbju(
                weight=weight, 
                height=height, 
                age=25,  # Можно добавить запрос возраста
                gender='male',  # Можно добавить запрос пола
                goal='maintenance'
            )
            
            self.db.update_user_metrics(user_id, height, weight, kbju['calories'])
            
            response = (
                "📊 Ваша рекомендуемая дневная норма КБЖУ:\n\n"
                f"• 🍽️ Калории: {kbju['calories']} ккал\n"
                f"• 🥩 Белки: {kbju['protein']} г\n"
                f"• 🥑 Жиры: {kbju['fat']} г\n"
                f"• 🍚 Углеводы: {kbju['carbs']} г\n\n"
                f"На один прием пищи (~3 приема):\n"
                f"• 🍽️ Калории: {kbju['per_meal']['calories']} ккал\n"
                f"• 🥩 Белки: {kbju['per_meal']['protein']} г\n"
                f"• 🥑 Жиры: {kbju['per_meal']['fat']} г\n"
                f"• 🍚 Углеводы: {kbju['per_meal']['carbs']} г\n\n"
                "Теперь вы можете отправлять фото еды для анализа! 📸"
            )
            
            await update.message.reply_text(response)
            self.user_manager.set_user_state(user_id, 'ready')
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        await update.message.reply_text("🔍 Анализирую фото...")
        
        # Анализ фото через Vision API
        analysis_result = self.vision.detect_food_items(bytes(photo_bytes))
        
        if not analysis_result['food_items']:
            await update.message.reply_text(
                "Не удалось определить продукты на фото. 😕\n"
                "Пожалуйста, введите название блюда вручную:"
            )
            self.user_manager.set_user_state(user_id, 'awaiting_food_name')
            return
        
        # Сохраняем результаты анализа
        self.user_manager.set_user_state(user_id, 'awaiting_confirmation', {
            'analysis_result': analysis_result,
            'photo_bytes': photo_bytes
        })
        
        response = "📸 На фото я определил:\n\n"
        total_calories = 0
        
        for item in analysis_result['food_items']:
            weight = analysis_result['estimated_weights'].get(item['name'].lower(), 100)
            kbju = self.calculator.calculate_food_kbju(item['name'], weight)
            
            response += (
                f"• {item['name'].title()} (~{weight}г):\n"
                f"  🍽️ {kbju['calories']} ккал | "
                f"🥩 {kbju['protein']}г | "
                f"🥑 {kbju['fat']}г | "
                f"🍚 {kbju['carbs']}г\n"
            )
            total_calories += kbju['calories']
        
        response += f"\n📊 Итого: {total_calories} ккал\n\nВсе верно?"
        
        await update.message.reply_text(response, reply_markup=get_confirm_keyboard())

    async def handle_manual_weight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)
        
        try:
            weight = float(update.message.text)
            food_name = user_data['food_name']
            
            kbju = self.calculator.calculate_food_kbju(food_name, weight)
            
            response = (
                f"📊 КБЖУ для {food_name} ({weight}г):\n\n"
                f"• 🍽️ Калории: {kbju['calories']} ккал\n"
                f"• 🥩 Белки: {kbju['protein']} г\n"
                f"• 🥑 Жиры: {kbju['fat']} г\n"
                f"• 🍚 Углеводы: {kbju['carbs']} г\n\n"
                "Выберите тип приема пищи:"
            )
            
            self.user_manager.set_user_state(user_id, 'awaiting_meal_type', {
                'food_name': food_name,
                'weight': weight,
                'kbju': kbju
            })
            
            await update.message.reply_text(response, reply_markup=get_meal_type_keyboard())
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")

    async def handle_food_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        food_name = update.message.text
        
        await update.message.reply_text(
            f"Введите примерный вес {food_name} в граммах:",
            reply_markup=remove_keyboard()
        )
        
        self.user_manager.set_user_state(user_id, 'awaiting_manual_weight', {
            'food_name': food_name
        })

    async def handle_trainer_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            trainer_id = int(update.message.text)
            
            # Добавляем связь тренер-ученик
            self.db.add_trainer_trainee(trainer_id, user_id)
            
            await update.message.reply_text(
                "✅ Вы успешно привязаны к тренеру!\n\n"
                "Теперь тренер будет видеть ваши результаты питания.",
                reply_markup=remove_keyboard()
            )
            
            self.user_manager.set_user_state(user_id, 'ready')
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный ID тренера:")

    async def daily_summary(self, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный отчет по питанию"""
        # Здесь можно добавить логику отправки ежедневных отчетов
        # тренерам и ученикам
        pass

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(Config.BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запускаем бота
        application.run_polling()

if __name__ == '__main__':
    bot = FithubBot()
    bot.run()
