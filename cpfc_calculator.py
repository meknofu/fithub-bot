import logging
from database import db
from config import Config

logger = logging.getLogger(__name__)

class CPFCCalculator:
    def __init__(self):
        self.db = db
    
    def calculate_daily_cpfc(self, weight, height, age, gender, activity_level='medium', goal='maintenance'):
        """Calculate recommended daily CPFC (Calories, Protein, Fat, Carbs)"""
        # Basal Metabolic Rate (BMR) using Mifflin-St Jeor Formula
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        # Activity level multipliers
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'medium': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        tdee = bmr * activity_multipliers.get(activity_level, 1.55)
        
        # Adjust for goal
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
            'calories': round(daily_calories),
            'protein': round(protein_grams),
            'fat': round(fat_grams),
            'carbs': round(carbs_grams)
        }
    
    def calculate_meal_cpfc(self, food_items):
        """Calculate CPFC for a meal (list of food items with name and weight)"""
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        for item in food_items:
            food_name = item['name']
            weight_grams = item['weight']
            
            # Get nutrition data for this food
            nutrition = self.get_food_nutrition(food_name, weight_grams)
            
            total_calories += nutrition['calories']
            total_protein += nutrition['protein']
            total_fat += nutrition['fat']
            total_carbs += nutrition['carbs']
            
            logger.info(f"Food: {food_name} ({weight_grams}g) - Cal: {nutrition['calories']}, P: {nutrition['protein']}, F: {nutrition['fat']}, C: {nutrition['carbs']}")
        
        result = {
            'calories': round(total_calories),
            'protein': round(total_protein, 1),
            'fat': round(total_fat, 1),
            'carbs': round(total_carbs, 1)
        }
        
        logger.info(f"Meal totals: {result}")
        return result
    
    def get_food_nutrition(self, food_name, weight_grams):
        """Get nutrition data for a specific food item"""
        # Try database first
        food_data = self.db.get_food_nutrition(food_name)
        
        if food_data:
            ratio = weight_grams / food_data.get('per_grams', 100)
            return {
                'calories': round(food_data['calories'] * ratio),
                'protein': round(food_data['protein'] * ratio, 1),
                'fat': round(food_data['fat'] * ratio, 1),
                'carbs': round(food_data['carbs'] * ratio, 1)
            }
        
        # Fallback to built-in database
        return self.get_average_nutrition(food_name, weight_grams)
    
    def get_average_nutrition(self, food_name, weight_grams):
        """Comprehensive food nutrition database (per 100g)"""
        
        nutrition_db = {
            # Eggs
            'egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            'eggs': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            'boiled egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            
            # Vegetables
            'carrot': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbs': 9.6},
            'carrots': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbs': 9.6},
            'tomato': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbs': 3.9},
            'cucumber': {'calories': 15, 'protein': 0.7, 'fat': 0.1, 'carbs': 3.6},
            'lettuce': {'calories': 15, 'protein': 1.4, 'fat': 0.2, 'carbs': 2.9},
            'salad': {'calories': 15, 'protein': 1.4, 'fat': 0.2, 'carbs': 2.9},
            'broccoli': {'calories': 34, 'protein': 2.8, 'fat': 0.4, 'carbs': 7},
            'spinach': {'calories': 23, 'protein': 2.9, 'fat': 0.4, 'carbs': 3.6},
            'potato': {'calories': 77, 'protein': 2, 'fat': 0.1, 'carbs': 17},
            'bell pepper': {'calories': 31, 'protein': 1, 'fat': 0.3, 'carbs': 6},
            
            # Fruits
            'orange': {'calories': 47, 'protein': 0.9, 'fat': 0.1, 'carbs': 12},
            'oranges': {'calories': 47, 'protein': 0.9, 'fat': 0.1, 'carbs': 12},
            'apple': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 14},
            'banana': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 23},
            'grape': {'calories': 69, 'protein': 0.7, 'fat': 0.2, 'carbs': 18},
            'strawberry': {'calories': 32, 'protein': 0.7, 'fat': 0.3, 'carbs': 8},
            'watermelon': {'calories': 30, 'protein': 0.6, 'fat': 0.2, 'carbs': 8},
            
            # Proteins
            'chicken': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0},
            'chicken breast': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0},
            'beef': {'calories': 250, 'protein': 26, 'fat': 15, 'carbs': 0},
            'pork': {'calories': 242, 'protein': 27, 'fat': 14, 'carbs': 0},
            'fish': {'calories': 120, 'protein': 20, 'fat': 5, 'carbs': 0},
            'salmon': {'calories': 208, 'protein': 20, 'fat': 13, 'carbs': 0},
            'tuna': {'calories': 132, 'protein': 28, 'fat': 1, 'carbs': 0},
            'shrimp': {'calories': 99, 'protein': 24, 'fat': 0.3, 'carbs': 0.2},
            
            # Grains & Carbs
            'rice': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28},
            'pasta': {'calories': 131, 'protein': 5, 'fat': 1.1, 'carbs': 25},
            'bread': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbs': 49},
            'oats': {'calories': 389, 'protein': 17, 'fat': 7, 'carbs': 66},
            'quinoa': {'calories': 120, 'protein': 4.4, 'fat': 1.9, 'carbs': 21},
            
            # Dairy
            'cheese': {'calories': 402, 'protein': 25, 'fat': 33, 'carbs': 1.3},
            'milk': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'yogurt': {'calories': 59, 'protein': 3.5, 'fat': 1.5, 'carbs': 6},
            
            # Prepared Foods
            'burger': {'calories': 295, 'protein': 17, 'fat': 12, 'carbs': 28},
            'pizza': {'calories': 266, 'protein': 11, 'fat': 10, 'carbs': 33},
            'sandwich': {'calories': 250, 'protein': 15, 'fat': 10, 'carbs': 25},
            'fries': {'calories': 312, 'protein': 3.4, 'fat': 15, 'carbs': 41},
            'french fries': {'calories': 312, 'protein': 3.4, 'fat': 15, 'carbs': 41},
            
            # Baked Goods
            'muffin': {'calories': 377, 'protein': 6.7, 'fat': 18, 'carbs': 47},
            'cookie': {'calories': 502, 'protein': 5.6, 'fat': 24, 'carbs': 67},
            'cake': {'calories': 257, 'protein': 3, 'fat': 10, 'carbs': 40},
            
            # Nuts & Seeds
            'almonds': {'calories': 579, 'protein': 21, 'fat': 50, 'carbs': 22},
            'walnuts': {'calories': 654, 'protein': 15, 'fat': 65, 'carbs': 14},
            'peanuts': {'calories': 567, 'protein': 26, 'fat': 49, 'carbs': 16},
            
            # Default fallback
            'default': {'calories': 150, 'protein': 8, 'fat': 5, 'carbs': 15}
        }
        
        # Normalize food name for lookup
        food_lower = food_name.lower().strip()
        
        # Try exact match first
        if food_lower in nutrition_db:
            selected = nutrition_db[food_lower]
        else:
            # Try partial match
            found = False
            for key in nutrition_db:
                if key in food_lower or food_lower in key:
                    selected = nutrition_db[key]
                    found = True
                    logger.info(f"Partial match: '{food_name}' matched to '{key}'")
                    break
            
            if not found:
                selected = nutrition_db['default']
                logger.warning(f"No match found for '{food_name}', using default values")
        
        # Calculate for given weight
        ratio = weight_grams / 100
        
        result = {
            'calories': round(selected['calories'] * ratio),
            'protein': round(selected['protein'] * ratio, 1),
            'fat': round(selected['fat'] * ratio, 1),
            'carbs': round(selected['carbs'] * ratio, 1)
        }
        
        logger.info(f"Nutrition for {food_name} ({weight_grams}g): {result}")
        return result
    
    def get_remaining_cpfc(self, user_id, date):
        """Calculate remaining CPFC for the day"""
        try:
            # Get user's daily target
            profile = self.db.get_user_profile(user_id)
            if not profile or not profile.get('daily_calories'):
                logger.warning(f"No profile found for user {user_id}")
                return None
            
            # Calculate target macros
            target_calories = profile['daily_calories']
            target_protein = (target_calories * Config.MACRO_RATIO['protein']) / 4
            target_fat = (target_calories * Config.MACRO_RATIO['fat']) / 9
            target_carbs = (target_calories * Config.MACRO_RATIO['carbs']) / 4
            
            # Get consumed for the day
            meals = self.db.get_daily_intake(user_id, date)
            
            consumed_calories = sum(meal.get('total_calories', 0) for meal in meals)
            consumed_protein = sum(meal.get('total_protein', 0) for meal in meals)
            consumed_fat = sum(meal.get('total_fat', 0) for meal in meals)
            consumed_carbs = sum(meal.get('total_carbs', 0) for meal in meals)
            
            return {
                'target_calories': target_calories,
                'target_protein': target_protein,
                'target_fat': target_fat,
                'target_carbs': target_carbs,
                'consumed_calories': consumed_calories,
                'consumed_protein': consumed_protein,
                'consumed_fat': consumed_fat,
                'consumed_carbs': consumed_carbs,
                'remaining_calories': target_calories - consumed_calories,
                'remaining_protein': target_protein - consumed_protein,
                'remaining_fat': target_fat - consumed_fat,
                'remaining_carbs': target_carbs - consumed_carbs
            }
        except Exception as e:
            logger.error(f"Error calculating remaining CPFC: {e}")
            return None
