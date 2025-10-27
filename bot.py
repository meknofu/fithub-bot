import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from config import Config
from database import db
from vision_api import VisionAPI
from kbju_calculator import KBJUCalculator
from user_manager import UserManager
from drink_manager import DrinkManager
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
        self.drink_manager = DrinkManager()

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
            f"Пожалуйста, выберите вашу роль:",
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
        elif state == 'awaiting_reference_object':
            await self.handle_reference_object(update, context)
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
        # Новые состояния для напитков
        elif state == 'awaiting_drink_method':
            await self.handle_drink_method(update, context)
        elif state == 'awaiting_drink_category':
            await self.handle_drink_category(update, context)
        elif state == 'awaiting_drink_selection':
            await self.handle_drink_selection(update, context)
        elif state == 'awaiting_drink_name':
            await self.handle_drink_name(update, context)
        elif state == 'awaiting_drink_volume':
            await self.handle_drink_volume(update, context)
        elif state == 'awaiting_drink_custom_volume':
            await self.handle_drink_custom_volume(update, context)
        elif state == 'awaiting_drink_confirmation':
            await self.handle_drink_confirmation(update, context)
        elif state == 'awaiting_barcode_photo':
            await self.handle_barcode_photo(update, context)
        else:
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
                "Отлично! Вы зарегистрированы как тренер. \n\n"
                "Теперь вы можете:\n"
                "• Добавлять учеников\n"
                "• Просматривать их рацион\n"
                "• Получать ежедневные отчеты о питании\n\n"
                "Для добавления ученика попросите его отправить вам свой ID.",
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
                "Отлично! Вы зарегистрированы как ученик.\n\n"
                "Для расчета вашей нормы КБЖУ мне нужны некоторые данные.\n\n"
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
                "Ваша рекомендуемая дневная норма КБЖУ:\n\n"
                f"• Калории: {kbju['calories']} ккал\n"
                f"• Белки: {kbju['protein']} г\n"
                f"• Жиры: {kbju['fat']} г\n"
                f"• Углеводы: {kbju['carbs']} г\n\n"
                f"На один прием пищи (~3 приема):\n"
                f"• Калории: {kbju['per_meal']['calories']} ккал\n"
                f"• Белки: {kbju['per_meal']['protein']} г\n"
                f"• Жиры: {kbju['per_meal']['fat']} г\n"
                f"• Углеводы: {kbju['per_meal']['carbs']} г\n\n"
                "Теперь вы можете отправлять фото еды для анализа!"
            )

            await update.message.reply_text(response)
            self.user_manager.set_user_state(user_id, 'ready')

        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        await update.message.reply_text("Анализирую фото...")

        try:
            # Используем старую проверенную функцию
            analysis_result = self.vision.detect_food_items(bytes(photo_bytes))

            # Сохраняем результаты анализа
            self.user_manager.set_user_state(user_id, 'awaiting_confirmation', {
                'analysis_result': analysis_result,
                'photo_bytes': photo_bytes
            })

            if not analysis_result['food_items']:
                await update.message.reply_text(
                    "Не удалось определить конкретные продукты на фото.\n"
                    "Пожалуйста, введите название блюда вручную:"
                )
                self.user_manager.set_user_state(user_id, 'awaiting_food_name')
                return

            response = "На фото я определил:\n\n"
            total_calories = 0
            total_weight = 0

            for item in analysis_result['food_items']:
                weight = analysis_result['estimated_weights'].get(item['name'].lower(), 100)
                kbju = self.calculator.calculate_food_kbju(item['name'], weight)

                response += (
                    f"• *{item['name'].title()}* (~{int(weight)}г):\n"
                    f" {kbju['calories']} ккал | "
                    f" {kbju['protein']}г | "
                    f" {kbju['fat']}г | "
                    f" {kbju['carbs']}г\n\n"
                )
                total_calories += kbju['calories']
                total_weight += weight

            # Добавляем информацию о референсах если они найдены
            if analysis_result.get('reference_detected'):
                response += "Определено с помощью ориентира на фото\n\n"
            else:
                response += "Совет: Для большей точности положите рядом вилку или телефон\n\n"

            response += f"*Итого:* {int(total_calories)} ккал (общий вес ~{int(total_weight)}г)\n\n*Все верно?*"

            await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_confirm_keyboard())

        except Exception as e:
            logger.error(f"Photo analysis error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при анализе фото.\n"
                "Пожалуйста, введите название блюда вручную:"
            )
            self.user_manager.set_user_state(user_id, 'awaiting_food_name')

    async def handle_reference_object(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)
        reference_choice = update.message.text

        reference_mapping = {
            'Вилка': 'fork',
            'Ложка': 'spoon',
            'Телефон': 'phone',
            'Карта': 'credit card',
            'Ладонь': 'hand',
            'Без ориентира': None
        }

        reference_object = reference_mapping.get(reference_choice)

        try:
            # Повторно анализируем фото с учетом референсного объекта
            analysis_result = self.vision.detect_food_items_with_reference(
                user_data['photo_bytes'],
                reference_object
            )

            # Сохраняем результаты
            self.user_manager.set_user_state(user_id, 'awaiting_confirmation', {
                'analysis_result': analysis_result,
                'photo_bytes': user_data['photo_bytes']
            })

            await self._send_food_analysis(update, analysis_result)

        except Exception as e:
            logger.error(f"Reference analysis error: {e}")
            await update.message.reply_text(
                "Ошибка при анализе. Попробуйте другое фото или введите название вручную:"
            )
            self.user_manager.set_user_state(user_id, 'awaiting_food_name')

    # Вспомогательный метод для отправки анализа
    async def _send_food_analysis(self, update, analysis_result):
        if not analysis_result['food_items']:
            await update.message.reply_text(
                "Не удалось определить конкретные продукты на фото.\n"
                "Пожалуйста, введите название блюда вручную:"
            )
            return

        response = "На фото я определил:\n\n"
        total_calories = 0

        for item in analysis_result['food_items']:
            weight = analysis_result['estimated_weights'].get(item['name'].lower(), 100)
            kbju = self.calculator.calculate_food_kbju(item['name'], weight)

            response += (
                f"• *{item['name'].title()}* (~{int(weight)}г):\n"
                f" {kbju['calories']} ккал | "
                f" {kbju['protein']}г | "
                f" {kbju['fat']}г | "
                f" {kbju['carbs']}г\n\n"
            )
            total_calories += kbju['calories']

        if analysis_result['reference_detected']:
            response += "Определено по ориентиру на фото\n\n"
        else:
            response += "Определено примерно\n\n"

        response += f"Итого: {int(total_calories)} ккал\n\nВсе верно?"

        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_confirm_keyboard())

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

            # Показываем итоговую информацию
            total_items = len(analysis_result.get('food_items', []))
            total_calories = sum(
                analysis_result['estimated_weights'].get(item['name'].lower(), 100) / 100 *
                self.calculator.calculate_food_kbju(item['name'], 100)['calories']
                for item in analysis_result.get('food_items', [])
            )

            await update.message.reply_text(
                f"Прием пищи сохранен!\n\n"
                f"• Сохранено компонентов: {total_items}\n"
                f"• Общие калории: {int(total_calories)} ккал\n\n"
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
                f"КБЖУ для {food_name} ({weight}г):\n\n"
                f"• Калории: {kbju['calories']} ккал\n"
                f"• Белки: {kbju['protein']}г\n"
                f"• Жиры: {kbju['fat']}г\n"
                f"• Углеводы: {kbju['carbs']}г\n\n"
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
            ' завтрак': 'breakfast',
            ' обед': 'lunch',
            ' перекус': 'snack',
            ' ужин': 'dinner'
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
            f"{meal_type_text} сохранен!\n\n"
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
                "Вы успешно привязаны к тренеру!\n\n"
                "Теперь тренер будет видеть ваши результаты питания.",
                reply_markup=remove_keyboard()
            )

            self.user_manager.set_user_state(user_id, 'ready')

        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный ID тренера:")

    # Команды для напитков
    async def drink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /drink - добавление напитка"""
        user_id = update.effective_user.id

        await update.message.reply_text(
            "Добавление напитка\n\n"
            "Введите название напитка или выберите категорию:",
            parse_mode='Markdown',
            reply_markup=get_drink_categories_keyboard()
        )

        self.user_manager.set_user_state(user_id, 'awaiting_drink_category')

    async def handle_drink_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора способа добавления напитка"""
        user_id = update.effective_user.id
        method = update.message.text

        if 'ввести название' in method.lower():
            await update.message.reply_text(
                "Ввод напитка\n\n"
                "Выберите категорию напитка:",
                parse_mode='Markdown',
                reply_markup=get_drink_categories_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_category')

        # УБИРАЕМ блок сканирования штрих-кода
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите способ из предложенных:",
                reply_markup=get_drink_method_keyboard()
            )

    async def handle_drink_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора категории напитка"""
        user_id = update.effective_user.id
        category = update.message.text

        if 'другое' in category.lower():
            await update.message.reply_text(
                "📝 *Ввод напитка*\n\n"
                "Введите название напитка:\n\n"
                "Примеры:\n"
                "• Капучино\n"
                "• Яблочный сок\n"
                "• Минеральная вода\n"
                "• Зеленый чай",
                parse_mode='Markdown',
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_name')

        else:
            # Показываем популярные напитки из выбранной категории
            await update.message.reply_text(
                f"Выберите напиток из категории {category}:",
                reply_markup=self._get_drinks_by_category(category)
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_selection')

    def _get_drinks_by_category(self, category):
        """Возвращает клавиатуру с напитками по категории"""
        from telegram import ReplyKeyboardMarkup

        drinks_by_category = {
            'вода': [
                ['Вода негазированная', 'Вода газированная'],
                ['Минеральная вода', '📝 Другая вода']
            ],
            'газировка': [
                ['Кола', 'Пепси'],
                ['Спрайт', 'Фанта'],
                ['Другая газировка']
            ],
            'кофе/чай': [
                ['Черный кофе', 'Кофе с молоком'],
                ['Капучино', 'Латте'],
                ['Черный чай', 'Зеленый чай'],
                ['Другой напиток']
            ],
            'сок': [
                ['Апельсиновый сок', 'Яблочный сок'],
                ['Томатный сок', 'Мультифруктовый сок'],
                ['Другой сок']
            ],
            'молочный напиток': [
                ['Молоко', 'Кефир'],
                ['Йогурт питьевой', 'Ряженка'],
                ['Другой молочный напиток']
            ],
            'алкоголь': [
                ['Пиво', 'Вино красное'],
                ['Вино белое', 'Шампанское'],
                ['Другой алкоголь']
            ],
            'энергетик': [
                ['Red Bull', 'Burn'],
                ['Adrenaline Rush', '📝 Другой энергетик']
            ],
            'спортивный напиток': [
                ['Изотоник', 'Протеиновый коктейль'],
                ['Другой спортивный напиток']
            ]
        }

        drinks = drinks_by_category.get(category.lower(), [['Ввести вручную']])
        return ReplyKeyboardMarkup(drinks, one_time_keyboard=True, resize_keyboard=True)

    async def handle_drink_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора конкретного напитка"""
        user_id = update.effective_user.id
        drink_name = update.message.text

        if 'другой' in drink_name.lower() or 'другая' in drink_name.lower():
            await update.message.reply_text(
                "Введите название напитка:",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_name')
        else:
            # Убираем эмодзи из названия для сохранения в базе
            clean_drink_name = ''.join(char for char in drink_name if char.isalpha() or char.isspace()).strip()

            await update.message.reply_text(
                f"Выберите объем для '{clean_drink_name}':",
                reply_markup=get_drink_volumes_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_volume', {
                'drink_name': clean_drink_name
            })

    async def handle_drink_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ручного ввода названия напитка"""
        user_id = update.effective_user.id
        drink_name = update.message.text

        if not drink_name.strip():
            await update.message.reply_text("Пожалуйста, введите название напитка:")
            return

        # Сохраняем название напитка и просим ввести объем
        self.user_manager.set_user_state(user_id, 'awaiting_drink_volume', {
            'drink_name': drink_name.strip()
        })

        await update.message.reply_text(
            f"Выберите объем для '{drink_name}':",
            reply_markup=get_drink_volumes_keyboard()
        )

    async def handle_drink_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода объема напитка"""
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)
        volume_text = update.message.text

        # Обработка выбора из клавиатуры объемов
        volume_mapping = {
            '250мл (стакан)': 250,
            '330мл (банка)': 330,
            '500мл (бутылка)': 500,
            '1000мл (литр)': 1000
        }

        if volume_text in volume_mapping:
            volume_ml = volume_mapping[volume_text]
        elif 'другой объем' in volume_text.lower():
            await update.message.reply_text(
                "Введите объем напитка в мл:\n\n"
                "Примеры:\n"
                "• 200 (для маленькой чашки)\n"
                "• 330 (для стандартной банки)\n"
                "• 500 (для бутылки)\n"
                "• 750 (для бутылки вина)",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_drink_custom_volume')
            return
        else:
            try:
                volume_ml = float(volume_text)
            except ValueError:
                await update.message.reply_text(
                    "Пожалуйста, выберите объем из списка или введите число:",
                    reply_markup=get_drink_volumes_keyboard()
                )
                return

        drink_name = user_data['drink_name']

        if volume_ml <= 0 or volume_ml > 5000:
            await update.message.reply_text(
                "Пожалуйста, введите корректный объем (1-5000 мл):",
                reply_markup=get_drink_volumes_keyboard()
            )
            return

        # Рассчитываем КБЖУ для напитка
        kbju = self.drink_manager.get_drink_kbju(drink_name, volume_ml)

        response = (
            f"{drink_name.title()} ({volume_ml}мл):\n\n"
            f"• Калории: {kbju['calories']} ккал\n"
            f"• Белки: {kbju['protein']}г\n"
            f"• Жиры: {kbju['fat']}г\n"
            f"• Углеводы: {kbju['carbs']}г\n\n"
            "Сохранить напиток?"
        )

        self.user_manager.set_user_state(user_id, 'awaiting_drink_confirmation', {
            'drink_name': drink_name,
            'volume_ml': volume_ml,
            'kbju': kbju
        })

        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_yes_no_keyboard())

    async def handle_drink_custom_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ручного ввода объема"""
        user_id = update.effective_user.id
        user_data = self.user_manager.get_user_data(user_id)

        try:
            volume_ml = float(update.message.text)
            drink_name = user_data['drink_name']

            if volume_ml <= 0 or volume_ml > 5000:
                await update.message.reply_text("Пожалуйста, введите корректный объем (1-5000 мл):")
                return

            # Рассчитываем КБЖУ для напитка
            kbju = self.drink_manager.get_drink_kbju(drink_name, volume_ml)

            response = (
                f"{drink_name.title()} ({volume_ml}мл):\n\n"
                f"• Калории: {kbju['calories']} ккал\n"
                f"• Белки: {kbju['protein']}г\n"
                f"• Жиры: {kbju['fat']}г\n"
                f"• Углеводы: {kbju['carbs']}г\n\n"
                "Сохранить напиток?"
            )

            self.user_manager.set_user_state(user_id, 'awaiting_drink_confirmation', {
                'drink_name': drink_name,
                'volume_ml': volume_ml,
                'kbju': kbju
            })

            await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_yes_no_keyboard())

        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число (объем в мл):")

    async def handle_drink_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения напитка"""
        user_id = update.effective_user.id
        message_text = update.message.text
        user_data = self.user_manager.get_user_data(user_id)

        if 'да' in message_text.lower():
            # Сохраняем напиток в базу
            self.db.add_meal(
                user_id=user_id,
                food_name=f"{user_data['drink_name']} (напиток)",
                weight_grams=user_data['volume_ml'],  # Используем мл как вес
                calories=user_data['kbju']['calories'],
                protein=user_data['kbju']['protein'],
                fat=user_data['kbju']['fat'],
                carbs=user_data['kbju']['carbs'],
                meal_type='drink'
            )

            await update.message.reply_text(
                "Напиток сохранен!\n\n"
                "Можете добавить еще напитков или еды.",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'ready')

        elif 'нет' in message_text.lower():
            await update.message.reply_text(
                "Напиток не сохранен.\n\n"
                "Можете добавить другой напиток или еду.",
                reply_markup=remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'ready')
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите Да или Нет:",
                reply_markup=get_yes_no_keyboard()
            )

    # Команды статистики и отчетов
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
    Помощь по использованию FITHUB

    Советы для лучшего распознавания:
    • Сфотографируйте еду сверху
    • Положите рядом вилку, телефон или карту для точного определения веса
    • Используйте хорошее освещение
    • Фотографируйте на однотонном фоне

    Основные команды:
    /start - Запустить бота
    /stats - Статистика питания
    /profile - Мой профиль
    /drink - Добавить напиток
    /id - Узнать свой ID для тренера

    Примеры названий блюд:
    • Курица гриль
    • Гречневая каша  
    • Салат цезарь
    • Рыба с овощами
    """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stats"""
        user_id = update.effective_user.id
        today = datetime.now().strftime('%Y-%m-%d')

        meals = self.db.get_daily_intake(user_id, today)

        if not meals:
            await update.message.reply_text("За сегодня еще нет записей о питании.")
            return

        total_calories = sum(meal['calories'] for meal in meals)
        total_protein = sum(meal['protein'] for meal in meals)
        total_fat = sum(meal['fat'] for meal in meals)
        total_carbs = sum(meal['carbs'] for meal in meals)

        # Получаем дневную норму пользователя
        user_data = self.db.get_user(user_id)
        daily_calories = user_data.get('daily_calories', 2000) if user_data else 2000

        progress = min(100, int((total_calories / daily_calories) * 100))

        # ОКРУГЛЯЕМ значения до сотых
        stats_text = f"""
    Статистика за сегодня

    Приемы пищи: {len(meals)}
    Съедено калорий: {round(total_calories, 2)} / {daily_calories} ккал
    Прогресс: {progress}%

    БЖУ за день:
    • Белки: {round(total_protein, 2)}г
    • Жиры: {round(total_fat, 2)}г  
    • Углеводы: {round(total_carbs, 2)}г

    *Последние приемы пищи:*
    """

        for meal in meals[-3:]:  # Последние 3 приема
            time = meal['created_at'].strftime('%H:%M') if meal['created_at'] else '--:--'
            stats_text += f"• {meal['food_name']} - {round(meal['calories'], 2)} ккал ({time})\n"

        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /profile"""
        user_id = update.effective_user.id
        user_data = self.db.get_user(user_id)

        if not user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start")
            return

        profile_text = f"""
    Ваш профиль

    Основные данные:
    • Рост: {user_data.get('height', 'Не указан')} см
    • Вес: {user_data.get('weight', 'Не указан')} кг
    • Тип: {'Тренер' if user_data.get('user_type') == 'trainer' else 'Ученик'}

    Рекомендуемая норма:
    • Калории: {round(user_data.get('daily_calories', 0), 2) if user_data.get('daily_calories') else 'Не рассчитано'} ккал/день
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
            await update.message.reply_text("За сегодня еще нет записей о питании.")
            return

        total_calories = sum(meal['calories'] for meal in meals)
        total_protein = sum(meal['protein'] for meal in meals)
        total_fat = sum(meal['fat'] for meal in meals)
        total_carbs = sum(meal['carbs'] for meal in meals)

        report_text = f"""
    Отчет по питанию за {today}

    Общая статистика:
    • Приемов пищи: {len(meals)}
    • Общие калории: {round(total_calories, 2)} ккал
    • Белки: {round(total_protein, 2)}г
    • Жиры: {round(total_fat, 2)}г
    • Углеводы: {round(total_carbs, 2)}г

    *Детали по приемам пищи:*
    """

        for i, meal in enumerate(meals, 1):
            time = meal['created_at'].strftime('%H:%M') if meal['created_at'] else '--:--'
            report_text += f"""
    {i}. *{meal['food_name']}* ({meal['weight_grams']}г)
       ️ {round(meal['calories'], 2)} ккал |  {round(meal['protein'], 2)}г |  {round(meal['fat'], 2)}г |  {round(meal['carbs'], 2)}г
        {time}
    """

        await update.message.reply_text(report_text, parse_mode='Markdown')

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /reset - сброс статистики за сегодня"""
        user_id = update.effective_user.id
        today = datetime.now().strftime('%Y-%m-%d')

        try:
            # Удаляем все записи о питании за сегодня
            with self.db.conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM meals WHERE user_id = %s AND DATE(created_at) = %s',
                    (user_id, today)
                )
                self.db.conn.commit()

            # Сбрасываем состояние пользователя
            self.user_manager.set_user_state(user_id, 'ready')

            await update.message.reply_text(
                "Статистика за сегодня сброшена!\n\n"
                "Все записи о приемах пищи удалены. "
                "Можете начать вести дневник питания заново.",
                reply_markup=remove_keyboard()
            )

        except Exception as e:
            logger.error(f"Reset error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при сбросе статистики. Попробуйте позже."
            )

    async def id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /id - показать ID пользователя"""
        user_id = update.effective_user.id

        await update.message.reply_text(
            f"Ваш ID: `{user_id}`\n\n"
            "Передайте этот ID вашему тренеру, чтобы он мог видеть вашу статистику питания.\n\n"
            "Тренер должен добавить вас командой:\n"
            "`/add_trainee ваш_id`",
            parse_mode='Markdown'
        )

    async def add_trainee_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /add_trainee - добавление ученика тренером"""
        user_id = update.effective_user.id

        # Проверяем, что пользователь - тренер
        user_data = self.db.get_user(user_id)
        if not user_data or user_data.get('user_type') != 'trainer':
            await update.message.reply_text(
                "Эта команда доступна только тренерам.\n\n"
                "Если вы тренер, сначала зарегистрируйтесь как тренер через /start"
            )
            return

        if not context.args:
            await update.message.reply_text(
                "Укажите ID ученика.\n\n"
                "Пример использования:\n"
                "`/add_trainee 123456789`\n\n"
                "Попросите ученика отправить команду /id чтобы получить его ID",
                parse_mode='Markdown'
            )
            return

        try:
            trainee_id = int(context.args[0])

            # Проверяем, что ученик существует
            trainee_data = self.db.get_user(trainee_id)
            if not trainee_data:
                await update.message.reply_text(
                    "Ученик с таким ID не найден.\n\n"
                    "Попросите ученика сначала запустить бота командой /start"
                )
                return

            # Добавляем связь тренер-ученик
            self.db.add_trainer_trainee(user_id, trainee_id)

            await update.message.reply_text(
                f"Ученик успешно добавлен!\n\n"
                f"ID ученика: {trainee_id}\n"
                f"Имя: {trainee_data.get('first_name', 'Неизвестно')}\n\n"
                "Теперь вы будете получать отчеты о его питании."
            )

        except ValueError:
            await update.message.reply_text(
                "Неверный формат ID.\n\n"
                "ID должен быть числом. Пример:\n"
                "`/add_trainee 123456789`",
                parse_mode='Markdown'
            )

    async def trainees_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /trainees - список учеников тренера"""
        user_id = update.effective_user.id

        # Проверяем, что пользователь - тренер
        user_data = self.db.get_user(user_id)
        if not user_data or user_data.get('user_type') != 'trainer':
            await update.message.reply_text(
                "Эта команда доступна только тренерам."
            )
            return

        try:
            trainees = self.db.get_trainees(user_id)

            if not trainees:
                await update.message.reply_text(
                    "У вас пока нет учеников.\n\n"
                    "Чтобы добавить ученика:\n"
                    "1. Попросите ученика отправить команду /id\n"
                    "2. Используйте команду /add_trainee [ID]"
                )
                return

            trainees_text = "Ваши ученики:\n\n"

            for trainee in trainees:
                today = datetime.now().strftime('%Y-%m-%d')
                trainee_meals = self.db.get_daily_intake(trainee['id'], today)
                total_calories = sum(meal['calories'] for meal in trainee_meals)

                trainees_text += (
                    f"*{trainee.get('first_name', 'Ученик')}* (ID: `{trainee['id']}`)\n"
                    f"• Калорий сегодня: {total_calories} ккал\n"
                    f"• Приемов пищи: {len(trainee_meals)}\n\n"
                )

            await update.message.reply_text(trainees_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Trainees command error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении списка учеников."
            )

    async def _check_meal_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет и отправляет напоминания о приемах пищи"""
        try:
            now = datetime.now()

            # Время напоминаний (часы, минуты, сообщение)
            reminder_times = [
                (8, 0,
                 "Время завтрака!\n\nНе забудьте позавтракать и записать прием пищи. Это поможет поддерживать метаболизм в течение дня."),
                (13, 0, "Время обеда!\n\nПора подкрепиться! Отправьте фото обеда или введите его вручную."),
                (19, 0,
                 "Время ужина!\n\nЛегкий ужин за 3-4 часа до сна поможет хорошо выспаться и сохранить форму."),
                (11, 0, "Время перекуса!\n\nНебольшой перекус поможет дождаться обеда без чувства голода."),
                (16, 0, "Время полдника!\n\nВторой перекус поддержит энергию до вечера.")
            ]

            for hour, minute, message in reminder_times:
                if now.hour == hour and now.minute == minute:
                    await self._send_reminders_to_active_users(context, message)

        except Exception as e:
            logger.error(f"Error in meal reminders: {e}")

    async def _send_reminders_to_active_users(self, context: ContextTypes.DEFAULT_TYPE, message):
        """Отправляет напоминания активным пользователям"""
        try:
            # Получаем список пользователей, которые сегодня были активны
            today = datetime.now().strftime('%Y-%m-%d')
            active_users = self._get_todays_active_users(today)

            for user_id in active_users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Meal reminder sent to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error sending reminders: {e}")

    def _get_todays_active_users(self, date):
        """Получает список пользователей, активных сегодня"""
        try:
            # Временно возвращаем пустой список чтобы не спамить
            # В реальной реализации здесь будет запрос к базе данных
            # Например: SELECT DISTINCT user_id FROM meals WHERE DATE(created_at) = %s
            return []
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    def run(self):
        """Запуск бота с напоминаниями"""
        # Создаем Application с JobQueue
        application = Application.builder().token(Config.BOT_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("report", self.report_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("id", self.id_command))
        application.add_handler(CommandHandler("drink", self.drink_command))
        application.add_handler(CommandHandler("add_trainee", self.add_trainee_command))
        application.add_handler(CommandHandler("trainees", self.trainees_command))

        # Обработчики сообщений
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запускаем напоминания если JobQueue доступен
        if application.job_queue:
            # Запускаем проверку напоминаний каждую минуту
            application.job_queue.run_repeating(
                self._check_meal_reminders,
                interval=60,  # Каждую минуту
                first=10  # Первый запуск через 10 секунд
            )
            logger.info("Meal reminders system started")
        else:
            logger.warning("JobQueue not available - meal reminders disabled")

        # Запускаем бота
        application.run_polling()


if __name__ == '__main__':
    bot = FithubBot()
    bot.run()
