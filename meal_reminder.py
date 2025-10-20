import datetime
import logging
from telegram.ext import ContextTypes
from database import db

logger = logging.getLogger(__name__)

class MealReminder:
    def __init__(self):
        self.meal_times = {
            'breakfast': datetime.time(hour=8, minute=0),   # 8:00
            'lunch': datetime.time(hour=13, minute=0),      # 13:00
            'dinner': datetime.time(hour=19, minute=0),     # 19:00
            'snack': datetime.time(hour=16, minute=0)       # 16:00
        }
    
    async def send_meal_reminder(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, meal_type: str):
        """Отправка напоминания о приеме пищи"""
        try:
            user = db.get_user(user_id)
            if not user:
                return
            
            meal_names = {
                'breakfast': 'завтрак',
                'lunch': 'обед', 
                'dinner': 'ужин',
                'snack': 'перекус'
            }
            
            meal_name = meal_names.get(meal_type, 'прием пищи')
            
            message = (
                f"🍽️ <b>Напоминание о {meal_name}</b>\n\n"
                f"Не забудьте внести данные о вашем питании!\n"
                f"Просто отправьте фото еды или введите название продукта."
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Отправлено напоминание о {meal_type} пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")
    
    async def send_daily_summary(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Отправка итогов за день"""
        try:
            user = db.get_user(user_id)
            if not user or user[3] != 'trainee':  # role в 4-й колонке
                return
            
            # Получаем итоги за сегодня
            calories, protein, fat, carbs = db.get_daily_summary(user_id)
            
            # Получаем цели пользователя
            goal_calories = user[10] or 2000  # daily_calories
            goal_protein = user[11] or 150    # protein_goal
            goal_fat = user[12] or 70         # fat_goal  
            goal_carbs = user[13] or 250      # carb_goal
            
            # Рассчитываем проценты
            calories_percent = (calories / goal_calories * 100) if goal_calories > 0 else 0
            protein_percent = (protein / goal_protein * 100) if goal_protein > 0 else 0
            fat_percent = (fat / goal_fat * 100) if goal_fat > 0 else 0
            carbs_percent = (carbs / goal_carbs * 100) if goal_carbs > 0 else 0
            
            # Создаем прогресс-бары
            def create_progress_bar(percent):
                filled = '█' * int(percent / 5)  # 20 символов = 100%
                empty = '░' * (20 - len(filled))
                return f"{filled}{empty} {percent:.1f}%"
            
            message = (
                f"📊 <b>Итоги за день</b>\n\n"
                f"🔥 Калории: {calories:.0f} / {goal_calories:.0f}\n"
                f"{create_progress_bar(calories_percent)}\n\n"
                f"💪 Белки: {protein:.1f}г / {goal_protein:.1f}г\n"
                f"{create_progress_bar(protein_percent)}\n\n"
                f"🥑 Жиры: {fat:.1f}г / {goal_fat:.1f}г\n"
                f"{create_progress_bar(fat_percent)}\n\n"
                f"🍚 Углеводы: {carbs:.1f}г / {goal_carbs:.1f}г\n"
                f"{create_progress_bar(carbs_percent)}\n\n"
            )
            
            if calories_percent >= 100:
                message += "🎯 <b>Дневная норма достигнута!</b> Отличная работа! 🎉"
            elif calories_percent >= 80:
                message += "💪 <b>Отличный прогресс!</b> Почти у цели!"
            else:
                message += "📈 <b>Хорошее начало!</b> Продолжайте в том же духе!"
            
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
            # Отправляем отчет тренеру
            trainer_id = user[14]  # trainer_id
            if trainer_id:
                await self.send_trainer_report(context, user_id, trainer_id, calories, protein, fat, carbs)
                
        except Exception as e:
            logger.error(f"Ошибка отправки итогов: {e}")
    
    async def send_trainer_report(self, context: ContextTypes.DEFAULT_TYPE, trainee_id: int, 
                                trainer_id: int, calories: float, protein: float, fat: float, carbs: float):
        """Отправка отчета тренеру"""
        try:
            trainee = db.get_user(trainee_id)
            if not trainee:
                return
            
            trainee_name = trainee[2]  # first_name
            
            message = (
                f"👤 <b>Отчет ученика: {trainee_name}</b>\n\n"
                f"📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"📊 Потребление за день:\n"
                f"• 🔥 {calories:.0f} ккал\n"
                f"• 💪 {protein:.1f}г белка\n"
                f"• 🥑 {fat:.1f}г жиров\n"
                f"• 🍚 {carbs:.1f}г углеводов"
            )
            
            await context.bot.send_message(
                chat_id=trainer_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки отчета тренеру: {e}")

# Глобальный экземпляр напоминаний
meal_reminder = MealReminder()
