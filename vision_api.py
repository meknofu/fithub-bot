from google.cloud import vision
import io
import logging
import json
import os
import random
from config import Config

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self):
        try:
            if Config.GOOGLE_VISION_API_KEY:
                from google.cloud.vision_v1 import ImageAnnotatorClient
                from google.api_core.client_options import ClientOptions
                
                client_options = ClientOptions(api_key=Config.GOOGLE_VISION_API_KEY)
                self.client = ImageAnnotatorClient(client_options=client_options)
                logger.info("Google Vision API initialized with API Key")
            else:
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized with default credentials")
                
        except Exception as e:
            logger.error(f"Google Vision initialization failed: {e}")
            self.client = None

    def detect_food_items(self, image_content):
        """Улучшенное определение еды с фильтрацией общих категорий"""
        if not self.client:
            return self._get_fallback_response()
            
        try:
            image = vision.Image(content=image_content)
            
            # Получаем разные типы анализа
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            
            food_items = []
            
            # Сначала объекты (более точные)
            for obj in objects:
                if self._is_specific_food_item(obj.name):
                    food_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score
                    })
            
            # Затем лейблы (фильтруем общие категории)
            for label in labels:
                if (self._is_specific_food_item(label.description) and 
                    label.score > 0.8 and  # Выше порог уверенности
                    not self._is_general_category(label.description)):
                    
                    # Проверяем дубликаты
                    if not any(item['name'].lower() == label.description.lower() for item in food_items):
                        food_items.append({
                            'name': label.description,
                            'confidence': label.score,
                            'type': 'label',
                            'score': label.score
                        })
            
            # Сортируем по уверенности и берем топ-3
            food_items.sort(key=lambda x: x['score'], reverse=True)
            food_items = food_items[:3]
            
            # Если ничего не нашли, используем fallback
            if not food_items:
                return self._get_fallback_response()
            
            detected_text = texts[0].description if texts else ""
            
            return {
                'food_items': food_items,
                'detected_text': detected_text,
                'estimated_weights': self.estimate_weights(food_items)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()

    def _is_specific_food_item(self, item_name):
        """Проверяет, является ли объект конкретной едой (не общей категорией)"""
        specific_foods = [
            # Фрукты
            'apple', 'banana', 'orange', 'grape', 'strawberry', 'watermelon',
            'pineapple', 'mango', 'pear', 'peach', 'cherry', 'kiwi',
            # Овощи
            'tomato', 'cucumber', 'carrot', 'potato', 'onion', 'pepper',
            'broccoli', 'cabbage', 'lettuce', 'spinach', 'corn',
            # Мясо и рыба
            'chicken', 'beef', 'pork', 'steak', 'salmon', 'tuna', 'shrimp',
            'fish', 'crab', 'lobster', 'sausage', 'bacon',
            # Готовые блюда
            'pizza', 'burger', 'sandwich', 'pasta', 'rice', 'sushi',
            'soup', 'salad', 'omelette', 'steak', 'curry',
            # Молочные продукты
            'cheese', 'milk', 'yogurt', 'butter', 'egg', 'eggs',
            # Прочее
            'bread', 'cake', 'cookie', 'chocolate', 'ice cream', 'coffee'
        ]
        
        item_lower = item_name.lower()
        return any(food in item_lower for food in specific_foods)

    def _is_general_category(self, item_name):
        """Фильтрует общие категории еды"""
        general_categories = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient', 'produce',
            'seafood', 'meat', 'fruit', 'vegetable', 'dairy', 'bread',
            'dessert', 'beverage', 'drink', 'snack', 'breakfast',
            'lunch', 'dinner', 'supper'
        ]
        
        item_lower = item_name.lower()
        return any(category == item_lower for category in general_categories)

    def _get_fallback_response(self):
        """Улучшенный fallback - просим ввести название вручную"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Улучшенная оценка веса"""
        estimated_weights = {}
        
        detailed_weight_estimates = {
            # Фрукты (в граммах)
            'apple': 180, 'banana': 120, 'orange': 130, 'grape': 150,
            'strawberry': 150, 'watermelon': 1000, 'pineapple': 900,
            'mango': 200, 'pear': 170, 'peach': 150, 'cherry': 100,
            'kiwi': 70,
            # Овощи
            'tomato': 120, 'cucumber': 150, 'carrot': 60, 'potato': 150,
            'onion': 100, 'pepper': 120, 'broccoli': 150, 'cabbage': 200,
            'lettuce': 100, 'spinach': 30, 'corn': 150,
            # Мясо и рыба
            'chicken': 150, 'beef': 200, 'pork': 150, 'steak': 250,
            'salmon': 150, 'tuna': 150, 'shrimp': 100, 'fish': 150,
            'crab': 200, 'lobster': 300, 'sausage': 100, 'bacon': 70,
            # Готовые блюда
            'pizza': 300, 'burger': 250, 'sandwich': 200, 'pasta': 250,
            'rice': 200, 'sushi': 100, 'soup': 350, 'salad': 200,
            'omelette': 150, 'curry': 300,
            # Молочные продукты
            'cheese': 30, 'milk': 200, 'yogurt': 150, 'butter': 15,
            'egg': 50, 'eggs': 50,
            # Прочее
            'bread': 40, 'cake': 120, 'cookie': 25, 'chocolate': 50,
            'ice cream': 100, 'coffee': 200
        }
        
        for item in food_items:
            item_name = item['name'].lower()
            found_weight = False
            
            # Ищем точное совпадение
            for food, weight in detailed_weight_estimates.items():
                if food in item_name:
                    estimated_weights[item_name] = weight
                    found_weight = True
                    break
            
            # Если не нашли, используем взвешенное значение по умолчанию
            if not found_weight:
                if 'soup' in item_name:
                    estimated_weights[item_name] = 300
                elif 'salad' in item_name:
                    estimated_weights[item_name] = 200
                elif 'drink' in item_name or 'beverage' in item_name:
                    estimated_weights[item_name] = 200
                else:
                    estimated_weights[item_name] = 150  # Средний вес
                
        return estimated_weights
