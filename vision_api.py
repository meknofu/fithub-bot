from google.cloud import vision
import io
import logging
import json
import os
from config import Config

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self):
        try:
            # Способ 1: Используем API ключ из переменной окружения
            if Config.GOOGLE_VISION_API_KEY:
                from google.cloud.vision_v1 import ImageAnnotatorClient
                from google.api_core.client_options import ClientOptions
                
                client_options = ClientOptions(api_key=Config.GOOGLE_VISION_API_KEY)
                self.client = ImageAnnotatorClient(client_options=client_options)
                logger.info("Google Vision API initialized with API Key")
                
            else:
                # Способ 2: Используем Service Account credentials
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized with default credentials")
                
        except Exception as e:
            logger.error(f"Google Vision initialization failed: {e}")
            self.client = None

    def detect_food_items(self, image_content):
        """Определяет продукты на фотографии через Google Vision API"""
        if not self.client:
            return self._get_fallback_response()
            
        try:
            image = vision.Image(content=image_content)
            
            # Детекция объектов
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            # Детекция текста
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            
            # Детекция лейблов (категорий)
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            
            food_items = []
            
            # Анализ объектов
            for obj in objects:
                if self._is_food_item(obj.name):
                    food_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object'
                    })
            
            # Анализ лейблов (категорий)
            for label in labels:
                if self._is_food_item(label.description) and label.score > 0.7:
                    # Проверяем, нет ли уже такого продукта
                    if not any(item['name'] == label.description for item in food_items):
                        food_items.append({
                            'name': label.description,
                            'confidence': label.score,
                            'type': 'label'
                        })
            
            detected_text = texts[0].description if texts else ""
            
            return {
                'food_items': food_items[:3],  # Ограничиваем 3 продуктами
                'detected_text': detected_text,
                'estimated_weights': self.estimate_weights(food_items)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()

    def _is_food_item(self, item_name):
        """Проверяет, является ли объект едой"""
        food_keywords = [
            'food', 'fruit', 'vegetable', 'meal', 'dish', 'cuisine',
            'apple', 'banana', 'orange', 'bread', 'pasta', 'rice',
            'pizza', 'hamburger', 'sandwich', 'salad', 'soup',
            'chicken', 'meat', 'beef', 'pork', 'fish', 'seafood',
            'egg', 'cheese', 'milk', 'yogurt', 'cake', 'cookie',
            'dessert', 'beverage', 'drink', 'coffee', 'tea'
        ]
        
        item_lower = item_name.lower()
        return any(keyword in item_lower for keyword in food_keywords)

    def _get_fallback_response(self):
        """Резервный ответ при ошибке Vision API"""
        return {
            'food_items': [{
                'name': 'food',
                'confidence': 0.8,
                'type': 'fallback'
            }],
            'detected_text': 'Используется базовый анализ',
            'estimated_weights': {'food': 200}
        }

    def estimate_weights(self, food_items):
        """Оценивает вес продуктов на основе их типа"""
        estimated_weights = {}
        
        weight_estimates = {
            'apple': 150, 'banana': 120, 'orange': 130, 'fruit': 150,
            'bread': 30, 'pasta': 100, 'rice': 150, 'grain': 150,
            'pizza': 300, 'hamburger': 200, 'sandwich': 150,
            'salad': 200, 'soup': 300, 'chicken': 150,
            'meat': 200, 'beef': 200, 'pork': 200, 'fish': 150,
            'egg': 50, 'cheese': 30, 'vegetable': 100,
            'cake': 100, 'cookie': 25, 'dessert': 100,
            'food': 200  # значение по умолчанию
        }
        
        for item in food_items:
            item_name = item['name'].lower()
            found_weight = False
            
            # Ищем точное совпадение
            for food, weight in weight_estimates.items():
                if food in item_name:
                    estimated_weights[item_name] = weight
                    found_weight = True
                    break
            
            # Если не нашли, используем значение по умолчанию
            if not found_weight:
                estimated_weights[item_name] = 200
                
        return estimated_weights
