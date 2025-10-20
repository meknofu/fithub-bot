import logging
import random
from typing import List, Dict
from usda_database import usda_db

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    def __init__(self):
        self.common_dishes = {
            # Завтраки
            'oatmeal': ['oatmeal', 'milk'],
            'scrambled_eggs': ['egg', 'bread'],
            'yogurt_bowl': ['yogurt', 'banana'],
            
            # Обеды
            'chicken_rice': ['chicken breast', 'rice', 'broccoli'],
            'pasta_dish': ['pasta', 'tomato'],
            'salad': ['tomato', 'cucumber', 'carrot'],
            
            # Ужины
            'fish_veg': ['salmon', 'potato', 'carrot'],
            'steak_dinner': ['beef steak', 'potato'],
        }
    
    def analyze_image(self, image_bytes: bytes) -> Dict:
        """
        Анализирует изображение и возвращает распознанное блюдо с граммовкой
        В реальной реализации здесь будет нейросеть
        """
        # В демо-режиме выбираем случайное блюдо
        dish_name, ingredients = random.choice(list(self.common_dishes.items()))
        
        # Определяем граммовки для ингредиентов
        detected_items = []
        total_calories = 0
        
        for ingredient in ingredients:
            # Случайный вес от 100 до 300 грамм
            weight = random.randint(100, 300)
            nutrition = usda_db.calculate_nutrition(ingredient, weight)
            
            detected_items.append({
                'name': ingredient,
                'weight': weight,
                'calories': nutrition['calories'],
                'protein': nutrition['protein'],
                'fat': nutrition['fat'],
                'carbs': nutrition['carbs']
            })
            
            total_calories += nutrition['calories']
        
        return {
            'dish_name': dish_name.replace('_', ' ').title(),
            'ingredients': detected_items,
            'total_weight': sum(item['weight'] for item in detected_items),
            'total_calories': total_calories,
            'confidence': round(random.uniform(0.7, 0.95), 2)
        }

# Глобальный экземпляр
vision_analyzer = VisionAnalyzer()
