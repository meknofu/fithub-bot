from database import db
from config import Config
import logging

logger = logging.getLogger(__name__)

class CPFCCalculator:
    """Calories, Protein, Fat, Carbs Calculator"""
    
    def __init__(self):
        self.db = db
    
    def calculate_daily_cpfc(self, weight, height, age, gender, activity_level='medium', goal='maintenance'):
        """Calculates recommended daily CPFC (Calories, Protein, Fat, Carbs)"""
        # Basal Metabolic Rate (BMR) using Mifflin-St Jeor equation
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        # Account for activity level
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'medium': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        tdee = bmr * activity_multipliers.get(activity_level, 1.55)
        
        # Adjust based on goal
        if goal == 'weight_loss':
            daily_calories = tdee * 0.85  # 15% deficit
        elif goal == 'weight_gain':
            daily_calories = tdee * 1.15  # 15% surplus
        else:  # maintenance
            daily_calories = tdee
        
        # Calculate macros
        protein_grams = (daily_calories * Config.MACRO_RATIO['protein']) / 4
        fat_grams = (daily_calories * Config.MACRO_RATIO['fat']) / 9
        carbs_grams = (daily_calories * Config.MACRO_RATIO['carbs']) / 4
        
        return {
            'calories': round(daily_calories, 2),
            'protein': round(protein_grams, 2),
            'fat': round(fat_grams, 2),
            'carbs': round(carbs_grams, 2)
        }
    
    def calculate_portion_cpfc(self, food_name, weight_grams):
        """Calculates CPFC for a specific food portion"""
        # Get nutrition data from database
        food_data = self.db.get_food_nutrition(food_name)
        
        if not food_data:
            return None
        
        # Nutrition data is typically per 100g
        multiplier = weight_grams / 100
        
        return {
            'name': food_name,
            'weight': weight_grams,
            'calories': round(food_data['calories'] * multiplier, 2),
            'protein': round(food_data['protein'] * multiplier, 2),
            'fat': round(food_data['fat'] * multiplier, 2),
            'carbs': round(food_data['carbs'] * multiplier, 2)
        }
    
    def calculate_meal_cpfc(self, food_items):
        """Calculates total CPFC for a meal from multiple food items"""
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        for item in food_items:
            item_cpfc = self.calculate_portion_cpfc(item['name'], item['weight'])
            if item_cpfc:
                total_calories += item_cpfc['calories']
                total_protein += item_cpfc['protein']
                total_fat += item_cpfc['fat']
                total_carbs += item_cpfc['carbs']
        
        return {
            'calories': round(total_calories, 2),
            'protein': round(total_protein, 2),
            'fat': round(total_fat, 2),
            'carbs': round(total_carbs, 2)
        }
    
    def get_remaining_cpfc(self, user_id, date):
        """Gets remaining CPFC for the day"""
        user_profile = self.db.get_user_profile(user_id)
        if not user_profile or not user_profile.get('daily_calories'):
            return None
        
        consumed = self.db.get_daily_intake(user_id, date)
        
        total_consumed_calories = sum(meal['calories'] for meal in consumed)
        total_consumed_protein = sum(meal['protein'] for meal in consumed)
        total_consumed_fat = sum(meal['fat'] for meal in consumed)
        total_consumed_carbs = sum(meal['carbs'] for meal in consumed)
        
        daily_target = self.calculate_daily_cpfc(
            user_profile['weight'],
            user_profile['height'],
            user_profile.get('age', 30),
            user_profile.get('gender', 'male'),
            user_profile.get('activity_level', 'medium'),
            user_profile.get('goal', 'maintenance')
        )
        
        return {
            'remaining_calories': round(daily_target['calories'] - total_consumed_calories, 2),
            'remaining_protein': round(daily_target['protein'] - total_consumed_protein, 2),
            'remaining_fat': round(daily_target['fat'] - total_consumed_fat, 2),
            'remaining_carbs': round(daily_target['carbs'] - total_consumed_carbs, 2),
            'consumed_calories': round(total_consumed_calories, 2),
            'consumed_protein': round(total_consumed_protein, 2),
            'consumed_fat': round(total_consumed_fat, 2),
            'consumed_carbs': round(total_consumed_carbs, 2),
            'target_calories': daily_target['calories'],
            'target_protein': daily_target['protein'],
            'target_fat': daily_target['fat'],
            'target_carbs': daily_target['carbs']
        }
