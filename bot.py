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
        
        logger.info(f"User {user_id} state: {state}, message: {message_text}")
        
        if state == 'awaiting_user_type':
            await self.handle_user_type(update, context)
        elif state == 'awaiting_height':
            await self.handle_height(update, context)
        elif state == 'awaiting_weight':
            await self.handle_weight(update, context)
        elif state == 'awaiting_trainer_id':
            await self.handle_trainer_id(update, context)
        elif state == 'awaiting_confirmation':
            await self.handle_confirmation(update, context)
        elif state == 'awaiting_food_name':
            await self.handle_food_name(update, context)
        elif state == 'awaiting_manual_weight':
            await self.handle_manual_weight(update, context)
        elif state == 'awaiting_meal_type':
            await self.handle_meal_type(update, context)
        else:
            # Если состояние не определено, предлагаем отправить фото
            await update.message.reply_text(
                "Отправьте фото еды для анализа или используйте команды.",
                reply_markup=remove_keyboard()
            )

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
        
        try:
            # Анализ фото через Vision API
            analysis_result = self.vision.detect_food_items(bytes(photo_bytes))
            
            # Сохраняем результаты анализа
            self.user_manager.set_user_state(user_id, 'awaiting_confirmation', {
                'analysis_result': analysis_result,
                'photo_bytes': photo_bytes
            })
            
            if not analysis_result['food_items']:
                await update.message.reply_text(
                    "Не удалось определить конкретные продукты на фото. 😕\n"
                    "Пожалуйста, введите название блюда вручную:"
                )
                self.user_manager.set_user_state(user_id, 'awaiting_food_name')
                return
            
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
                    f"🍚 {kbju['carbs']}г\n\n"
                )
                total_calories += kbju['calories']
            
            response += f"📊 Итого: {total_calories} ккал\n\nВсе верно?"
            
            await update.message.reply_text(response, reply_markup=get_confirm_keyboard())
            
        except Exception as e:
            logger.error(f"Photo analysis error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при анализе фото. 😕\n"
                "Пожалуйста, введите название блюда вручную:"
            )
            self.user_manager.set_user_state(user_id, 'awaiting_food_name')

    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения результатов анализа"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        if 'да, все верно' in message_text.lower():
            user_data = self.user_manager.get_user_data(user_id)
            analysis_result = user_data.get('analysis_result', {})
            
            # Сохраняем все распознанные продукты
            for item in analysis_result.get('food_items', []):
                weight = analysis_result['estimated_weights'].get(item['name'].lower(), 100)
                kbju = self.calculator.calculate_food_kbju(item['name'], weight)
                
                self.db.add_meal(
                    user_id=user_id,
                    food_name=item['name'],
                    weight_grams=weight,
                    calories=kbju['calories'],
                    protein=kbju['protein'],
                    fat=kbju['fat'],
                    carbs=kbju['carbs'],
                    meal_type='detected'
                )
            
            await update.message.reply_text(
                "✅ Прием пищи сохранен!\n\n"
                "Вы можете отправить следующее фото или посмотреть статистику.",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'ready')
            
        elif 'нет, исправить вручную' in message_text.lower():
            await update.message.reply_text(
                "Введите название блюда вручную:\n\n"
                "Примеры: курица гриль, гречневая каша, салат цезарь, рыба с овощами",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_food_name')
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите вариант из клавиатуры:",
                reply_markup=get_confirm_keyboard()
            )

    async def handle_food_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ручного ввода названия блюда"""
        user_id = update.effective_user.id
        food_name = update.message.text
        
        if not food_name or len(food_name.strip()) == 0:
            await update.message.reply_text("Пожалуйста, введите название блюда:")
            return
        
        # Сохраняем название блюда и просим ввести вес
        self.user_manager.set_user_state(user_id, 'awaiting_manual_weight', {
            'food_name': food_name.strip()
        })
        
        await update.message.reply_text(
            f"Введите вес '{food_name}' в граммах:",
            reply_markup=remove_keyboard()
        )

    async def handle_manual_weight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ручного ввода веса"""
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)
        
        try:
            weight = float(update.message.text)
            food_name = user_data['food_name']
            
            if weight <= 0 or weight > 5000:
                await update.message.reply_text("Пожалуйста, введите корректный вес (1-5000 грамм):")
                return
            
            # Рассчитываем КБЖУ
            kbju = self.calculator.calculate_food_kbju(food_name, weight)
            
            response = (
                f"📊 КБЖУ для {food_name} ({weight}г):\n\n"
                f"• 🍽️ Калории: {kbju['calories']} ккал\n"
                f"• 🥩 Белки: {kbju['protein']}г\n"
                f"• 🥑 Жиры: {kbju['fat']}г\n"
                f"• 🍚 Углеводы: {kbju['carbs']}г\n\n"
                "Выберите тип приема пищи:"
            )
            
            self.user_manager.set_user_state(user_id, 'awaiting_meal_type', {
                'food_name': food_name,
                'weight': weight,
                'kbju': kbju
            })
            
            await update.message.reply_text(response, reply_markup=get_meal_type_keyboard())
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число (вес в граммах):")

    async def handle_meal_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа приема пищи"""
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)
        meal_type_text = update.message.text
        
        meal_type_mapping = {
            '🍳 завтрак': 'breakfast',
            '🍲 обед': 'lunch', 
            '🍰 перекус': 'snack',
            '🍽️ ужин': 'dinner'
        }
        
        meal_type_en = meal_type_mapping.get(meal_type_text.lower(), 'other')
        
        # Сохраняем в базу
        self.db.add_meal(
            user_id=user_id,
            food_name=user_data['food_name'],
            weight_grams=user_data['weight'],
            calories=user_data['kbju']['calories'],
            protein=user_data['kbju']['protein'],
            fat=user_data['kbju']['fat'],
            carbs=user_data['kbju']['carbs'],
            meal_type=meal_type_en
        )
        
        await update.message.reply_text(
            f"✅ {meal_type_text} сохранен!\n\n"
            "Можете отправить следующее фото или посмотреть статистику.",
            reply_markup=remove_keyboard()
        )
        self.user_manager.set_user_state(user_id, 'ready')

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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_text = """
    🤖 *Помощь по использованию FITHUB*

    *Основные команды:*
    /start - Запустить бота
    /stats - Статистика питания
    /profile - Мой профиль
    /report - Отчет за сегодня

    *Как использовать:*
    1. Отправьте фото еды 📸
    2. Бот определит продукты и КБЖУ
    3. Подтвердите или исправьте вручную
    4. Выберите тип приема пищи

    *Что умеет бот:*
    • Распознавать еду на фото
    • Рассчитывать калории, белки, жиры, углеводы
    • Давать рекомендации по нормам
    • Вести дневник питания
    • Отправлять отчеты тренеру

    *Примеры названий блюд для ручного ввода:*
    • Курица гриль
    • Гречневая каша  
    • Салат цезарь
    • Рыба с овощами
    • Творог с фруктами
    """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stats"""
        user_id = update.effective_user.id
        today = datetime.now().strftime('%Y-%m-%d')

        meals = self.db.get_daily_intake(user_id, today)

        if not meals:
            await update.message.reply_text("📊 За сегодня еще нет записей о питании.")
            return

        total_calories = sum(meal['calories'] for meal in meals)
        total_protein = sum(meal['protein'] for meal in meals)
        total_fat = sum(meal['fat'] for meal in meals)
        total_carbs = sum(meal['carbs'] for meal in meals)

        # Получаем дневную норму пользователя
        user_data = self.db.get_user(user_id)
        daily_calories = user_data.get('daily_calories', 2000) if user_data else 2000

        progress = min(100, int((total_calories / daily_calories) * 100))

        stats_text = f"""
    📊 *Статистика за сегодня*

    *Приемы пищи:* {len(meals)}
    *Съедено калорий:* {total_calories} / {daily_calories} ккал
    *Прогресс:* {progress}%

    *БЖУ за день:*
    • 🥩 Белки: {total_protein}г
    • 🥑 Жиры: {total_fat}г  
    • 🍚 Углеводы: {total_carbs}г

    *Последние приемы пищи:*
    """

        for meal in meals[-3:]:  # Последние 3 приема
            time = meal['created_at'].strftime('%H:%M') if meal['created_at'] else '--:--'
            stats_text += f"• {meal['food_name']} - {meal['calories']} ккал ({time})\n"

        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /profile"""
        user_id = update.effective_user.id
        user_data = self.db.get_user(user_id)

        if not user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start")
            return

        profile_text = f"""
    👤 *Ваш профиль*

    *Основные данные:*
    • Рост: {user_data.get('height', 'Не указан')} см
    • Вес: {user_data.get('weight', 'Не указан')} кг
    • Тип: {'🏋️ Тренер' if user_data.get('user_type') == 'trainer' else '🧑‍🎓 Ученик'}

    *Рекомендуемая норма:*
    • 🍽️ Калории: {user_data.get('daily_calories', 'Не рассчитано')} ккал/день
    """

        if user_data.get('user_type') == 'trainee' and user_data.get('trainer_id'):
            profile_text += f"• Тренер: ID {user_data.get('trainer_id')}"

        await update.message.reply_text(profile_text, parse_mode='Markdown')

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /report"""
        user_id = update.effective_user.id
        today = datetime.now().strftime('%Y-%m-%d')

        meals = self.db.get_daily_intake(user_id, today)

        if not meals:
            await update.message.reply_text("📝 За сегодня еще нет записей о питании.")
            return

        total_calories = sum(meal['calories'] for meal in meals)
        total_protein = sum(meal['protein'] for meal in meals)
        total_fat = sum(meal['fat'] for meal in meals)
        total_carbs = sum(meal['carbs'] for meal in meals)

        report_text = f"""
    📈 *Отчет по питанию за {today}*

    *Общая статистика:*
    • Приемов пищи: {len(meals)}
    • Общие калории: {total_calories} ккал
    • Белки: {total_protein}г
    • Жиры: {total_fat}г
    • Углеводы: {total_carbs}г

    *Детали по приемам пищи:*
    """

        for i, meal in enumerate(meals, 1):
            time = meal['created_at'].strftime('%H:%M') if meal['created_at'] else '--:--'
            report_text += f"""
    {i}. *{meal['food_name']}* ({meal['weight_grams']}г)
       🍽️ {meal['calories']} ккал | 🥩 {meal['protein']}г | 🥑 {meal['fat']}г | 🍚 {meal['carbs']}г
       ⏰ {time}
    """

        await update.message.reply_text(report_text, parse_mode='Markdown')

    async def daily_summary(self, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный отчет по питанию"""
        pass

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(Config.BOT_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("report", self.report_command))

        # Обработчики сообщений
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запускаем бота
        application.run_polling()

if __name__ == '__main__':
    bot = FithubBot()
    bot.run()
