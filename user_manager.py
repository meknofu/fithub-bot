
from database import db
from kbju_calculator import KBJUCalculator
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.db = db
        self.calculator = KBJUCalculator()
        self.user_states = {}

    def set_user_state(self, user_id, state, data=None):
        """Устанавливает состояние пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        self.user_states[user_id]['state'] = state
        if data:
            self.user_states[user_id]['data'] = data

    def get_user_state(self, user_id):
        """Получает состояние пользователя"""
        return self.user_states.get(user_id, {}).get('state')

    def get_user_data(self, user_id):
        """Получает данные пользователя"""
        return self.user_states.get(user_id, {}).get('data', {})

    async def start_meal_reminders(self, application):
        """Запускает напоминания о приемах пищи"""
        while True:
            now = datetime.now()
            
            # Время напоминаний (часы, минуты, сообщение)
            reminder_times = [
                (8, 0, "🍳 *Время завтрака!*\n\nНе забудьте позавтракать и записать прием пищи. Это поможет поддерживать метаболизм в течение дня."),
                (13, 0, "🍲 *Время обеда!*\n\nПора подкрепиться! Отправьте фото обеда или введите его вручную."),
                (19, 0, "🍽️ *Время ужина!*\n\nЛегкий ужин за 3-4 часа до сна поможет хорошо выспаться и сохранить форму."),
                (11, 0, "☕ *Время перекуса!*\n\nНебольшой перекус поможет дождаться обеда без чувства голода."),
                (16, 0, "🍎 *Время полдника!*\n\nВторой перекус поддержит энергию до вечера.")
            ]
            
            for hour, minute, message in reminder_times:
                if now.hour == hour and now.minute == minute:
                    await self._send_reminders_to_all_users(application, message)
                    await asyncio.sleep(60)  # Ждем минуту чтобы не отправлять повторно
            
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд

    async def _send_reminders_to_all_users(self, application, message):
        """Отправляет напоминания всем активным пользователям"""
        try:
            # Здесь нужно получить список всех пользователей из базы
            # Пока отправляем только тем, кто сегодня активен
            active_users = self._get_active_users()
            
            for user_id in active_users:
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Reminder sent to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in reminder system: {e}")

    def _get_active_users(self):
        """Получает список активных пользователей (упрощенная версия)"""
        try:
            # В реальной реализации здесь запрос к базе
            # Сейчас возвращаем пустой список чтобы не спамить
            return []
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    def get_daily_summary(self, user_id):
        """Получает итог рациона за день"""
        today = datetime.now().strftime('%Y-%m-%d')
        meals = self.db.get_daily_intake(user_id, today)
        
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        for meal in meals:
            total_calories += meal['calories']
            total_protein += meal['protein']
            total_fat += meal['fat']
            total_carbs += meal['carbs']
        
        return {
            'date': today,
            'meals': meals,
            'total_calories': total_calories,
            'total_protein': total_protein,
            'total_fat': total_fat,
            'total_carbs': total_carbs
        }
