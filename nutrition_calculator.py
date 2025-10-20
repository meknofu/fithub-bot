import logging
from typing import Dict

logger = logging.getLogger(__name__)

class NutritionCalculator:
    def __init__(self):
        pass
    
    def calculate_bmr(self, weight: float, height: float, age: int, gender: str) -> float:
        """Расчет базового метаболизма (BMR) по формуле Миффлина-Сан Жеора"""
        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        return bmr
    
    def calculate_daily_calories(self, bmr: float, goal: str, activity_level: float = 1.375) -> float:
        """Расчет дневной нормы калорий"""
        maintenance = bmr * activity_level
        
        if goal == 'lose':
            return maintenance * 0.85  # Дефицит 15%
        elif goal == 'gain':
            return maintenance * 1.15  # Профицит 15%
        else:  # maintain
            return maintenance
    
    def calculate_macros(self, calories: float, goal: str) -> Dict[str, float]:
        """Расчет макросов (белки, жиры, углеводы)"""
        if goal == 'lose':
            # Высокобелковая диета для похудения
            protein_ratio = 0.35
            fat_ratio = 0.25
            carb_ratio = 0.40
        elif goal == 'gain':
            # Высокоуглеводная диета для набора массы
            protein_ratio = 0.30
            fat_ratio = 0.25
            carb_ratio = 0.45
        else:  # maintain
            protein_ratio = 0.30
            fat_ratio = 0.30
            carb_ratio = 0.40
            
        return {
            'protein_grams': (calories * protein_ratio) / 4,  # 1г белка = 4 ккал
            'fat_grams': (calories * fat_ratio) / 9,         # 1г жира = 9 ккал
            'carbs_grams': (calories * carb_ratio) / 4,      # 1г углеводов = 4 ккал
            'protein_percent': protein_ratio * 100,
            'fat_percent': fat_ratio * 100,
            'carbs_percent': carb_ratio * 100
        }
    
    def calculate_meal_recommendations(self, daily_calories: float, daily_protein: float, 
                                     daily_fat: float, daily_carbs: float, meals_per_day: int = 3) -> Dict:
        """Рекомендации на один прием пищи"""
        return {
            'calories_per_meal': daily_calories / meals_per_day,
            'protein_per_meal': daily_protein / meals_per_day,
            'fat_per_meal': daily_fat / meals_per_day,
            'carbs_per_meal': daily_carbs / meals_per_day,
            'meals_per_day': meals_per_day
        }
    
    def get_activity_levels(self) -> Dict[str, float]:
        """Уровни физической активности"""
        return {
            'sedentary': 1.2,      # Минимальная активность
            'light': 1.375,         # Легкие упражнения 1-3 дня/неделю
            'moderate': 1.55,       # Умеренные упражнения 3-5 дней/неделю
            'active': 1.725,        # Тяжелые упражнения 6-7 дней/неделю
            'very_active': 1.9      # Очень тяжелые упражнения + физическая работа
        }

# Глобальный экземпляр калькулятора
nutrition_calc = NutritionCalculator()
