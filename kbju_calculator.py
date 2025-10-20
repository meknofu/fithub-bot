from database import db
from config import Config
import logging

logger = logging.getLogger(__name__)

class KBJUCalculator:
    def __init__(self):
        self.db = db

    def calculate_daily_kbju(self, weight, height, age, gender, activity_level='medium', goal='maintenance'):
        """Рассчитывает рекомендуемое дневное КБЖУ"""
        # Базальный метаболизм (BMR) по формуле Миффлина-Сан Жеора
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        # Учет уровня активности
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'medium': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        tdee = bmr * activity_multipliers.get(activity_level, 1.55)
        
        # Корректировка по цели
        if goal == 'weight_loss':
            daily_calories = tdee * 0.85  # дефицит 15%
        elif goal == 'weight_gain':
            daily_calories = tdee * 1.15  # профицит 15%
        else:  # maintenance
            daily_calories = tdee
        
        # Расчет БЖУ
        protein_grams = (daily_calories * Config.MACRO_RATIO['protein']) / 4
        fat_grams = (daily_calories * Config.MACRO_RATIO['fat']) / 9
        carbs_grams = (daily_calories * Config.MACRO_RATIO['carbs']) / 4
        
        return {
            'calories': round(daily_calories),
            'protein': round(protein_grams),
            'fat': round(fat_grams),
            'carbs': round(carbs_grams),
            'per_meal': self.calculate_per_meal(daily_calories, protein_grams, fat_grams, carbs_grams)
        }
    
    def calculate_per_meal(self, daily_calories, protein, fat, carbs, meals_per_day=3):
        """Рассчитывает КБЖУ на один прием пищи"""
        return {
            'calories': round(daily_calories / meals_per_day),
            'protein': round(protein / meals_per_day),
            'fat': round(fat / meals_per_day),
            'carbs': round(carbs / meals_per_day)
        }
    
    def calculate_food_kbju(self, food_name, weight_grams):
        """Рассчитывает КБЖУ для конкретного продукта"""
        food_item = self.db.search_food(food_name)
        if not food_item:
            # Если продукт не найден, используем средние значения
            return self.get_average_kbju(food_name, weight_grams)
        
        food_data = food_item[0]
        ratio = weight_grams / 100
        
        return {
            'calories': round(food_data['calories_per_100g'] * ratio),
            'protein': round(food_data['protein_per_100g'] * ratio, 1),
            'fat': round(food_data['fat_per_100g'] * ratio, 1),
            'carbs': round(food_data['carbs_per_100g'] * ratio, 1)
        }
    
    def get_average_kbju(self, food_name, weight_grams):
        """Улучшенная база средних значений КБЖУ"""
        # Расширенная база продуктов
        average_values = {
            # Рыба и морепродукты
            'рыба': {'calories': 120, 'protein': 20, 'fat': 5, 'carbs': 0},
            'лосось': {'calories': 208, 'protein': 20, 'fat': 13, 'carbs': 0},
            'тунец': {'calories': 132, 'protein': 28, 'fat': 1, 'carbs': 0},
            'креветки': {'calories': 85, 'protein': 18, 'fat': 1, 'carbs': 0},
            'семга': {'calories': 208, 'protein': 20, 'fat': 13, 'carbs': 0},
            'окунь': {'calories': 91, 'protein': 19, 'fat': 0.9, 'carbs': 0},
            'карп': {'calories': 127, 'protein': 18, 'fat': 5.6, 'carbs': 0},
            'судак': {'calories': 84, 'protein': 19, 'fat': 0.8, 'carbs': 0},
            # Мясо и птица
            'курица': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0},
            'говядина': {'calories': 250, 'protein': 26, 'fat': 15, 'carbs': 0},
            'свинина': {'calories': 242, 'protein': 27, 'fat': 14, 'carbs': 0},
            'индейка': {'calories': 135, 'protein': 29, 'fat': 0.7, 'carbs': 0},
            # Гарниры
            'рис': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28},
            'гречка': {'calories': 110, 'protein': 4.2, 'fat': 1.1, 'carbs': 21},
            'картофель': {'calories': 77, 'protein': 2, 'fat': 0.1, 'carbs': 17},
            'макароны': {'calories': 131, 'protein': 5, 'fat': 1.1, 'carbs': 25},
            'овсянка': {'calories': 68, 'protein': 2.4, 'fat': 1.4, 'carbs': 12},
            'пшено': {'calories': 119, 'protein': 3.5, 'fat': 1, 'carbs': 23},
            # Овощи
            'салат': {'calories': 15, 'protein': 1.4, 'fat': 0.2, 'carbs': 2.9},
            'овощи': {'calories': 40, 'protein': 2, 'fat': 0.3, 'carbs': 8},
            'помидоры': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbs': 3.9},
            'огурцы': {'calories': 15, 'protein': 0.7, 'fat': 0.1, 'carbs': 3.6},
            'морковь': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbs': 9.6},
            'капуста': {'calories': 25, 'protein': 1.3, 'fat': 0.1, 'carbs': 5.8},
            # Фрукты
            'яблоко': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 14},
            'банан': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 23},
            'апельсин': {'calories': 47, 'protein': 0.9, 'fat': 0.1, 'carbs': 12},
            # Молочные продукты
            'творог': {'calories': 159, 'protein': 18, 'fat': 9, 'carbs': 3},
            'молоко': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'йогурт': {'calories': 59, 'protein': 3.5, 'fat': 1.5, 'carbs': 6},
            'сыр': {'calories': 402, 'protein': 25, 'fat': 33, 'carbs': 1.3},
            'кефир': {'calories': 41, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            # Яйца
            'яйцо': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            # Хлеб и выпечка
            'хлеб': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbs': 49},
            'булка': {'calories': 270, 'protein': 8, 'fat': 3.5, 'carbs': 50},
            # По умолчанию
            'default': {'calories': 200, 'protein': 10, 'fat': 8, 'carbs': 20}
        }
        
        food_lower = food_name.lower()
        for key in average_values:
            if key in food_lower:
                selected = average_values[key]
                break
        else:
            selected = average_values['default']
        
        ratio = weight_grams / 100
        return {
            'calories': round(selected['calories'] * ratio),
            'protein': round(selected['protein'] * ratio, 1),
            'fat': round(selected['fat'] * ratio, 1),
            'carbs': round(selected['carbs'] * ratio, 1)
        }
