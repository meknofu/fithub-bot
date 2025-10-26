from database import db
from kbju_calculator import KBJUCalculator
import logging
from datetime import datetime

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
