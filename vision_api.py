from google.cloud import vision
import io
import logging
from config import Config

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()

    def detect_food_items(self, image_content):
        """Определяет продукты на фотографии"""
        try:
            image = vision.Image(content=image_content)
            
            # Детекция объектов
            objects = self.client.object_localization(image=image).localized_object_annotations
            
            # Детекция текста (для возможного распознавания названий)
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            
            food_items = []
            
            for obj in objects:
                if obj.name.lower() in self.get_food_categories():
                    food_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'bounding_box': obj.bounding_poly
                    })
            
            detected_text = texts[0].description if texts else ""
            
            return {
                'food_items': food_items,
                'detected_text': detected_text,
                'estimated_weights': self.estimate_weights(food_items)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return {'food_items': [], 'detected_text': '', 'estimated_weights': {}}

    def get_food_categories(self):
        """Возвращает список категорий еды"""
        return [
            'apple', 'banana', 'orange', 'bread', 'pasta', 'rice',
            'pizza', 'hamburger', 'sandwich', 'salad', 'soup',
            'chicken', 'meat', 'fish', 'egg', 'cheese', 'milk',
            'yogurt', 'vegetable', 'fruit', 'cake', 'cookie'
        ]

    def estimate_weights(self, food_items):
        """Оценивает вес продуктов на основе их размера"""
        estimated_weights = {}
        
        # Базовая эвристика для оценки веса
        weight_estimates = {
            'apple': 150, 'banana': 120, 'orange': 130,
            'bread': 30, 'pasta': 100, 'rice': 150,
            'pizza': 300, 'hamburger': 200, 'sandwich': 150,
            'salad': 200, 'soup': 300, 'chicken': 150,
            'meat': 200, 'fish': 150, 'egg': 50,
            'cheese': 30, 'vegetable': 100, 'fruit': 150
        }
        
        for item in food_items:
            item_name = item['name'].lower()
            if item_name in weight_estimates:
                estimated_weights[item_name] = weight_estimates[item_name]
            else:
                estimated_weights[item_name] = 100  # средний вес по умолчанию
                
        return estimated_weights
