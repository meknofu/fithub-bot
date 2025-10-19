import os
import base64
import logging
from google.cloud import vision
from google.oauth2 import service_account
import io

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self, credentials_path=None):
        self.credentials_path = credentials_path
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Инициализация клиента Google Vision API"""
        try:
            # Сначала пробуем найти credentials файл
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Google Vision API инициализирован с файлом credentials")
            
            # Пробуем переменные окружения (для хостинга)
            elif os.getenv('GOOGLE_CREDENTIALS_JSON'):
                import json
                credentials_info = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Google Vision API инициализирован с переменными окружения")
            
            # Автоматическое обнаружение (для Google Cloud)
            else:
                self.client = vision.ImageAnnotatorClient()
                logger.info("✅ Google Vision API инициализирован с автоматической аутентификацией")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Google Vision API: {e}")
            self.client = None
    
    def detect_food_items(self, image_content):
        """Определение еды на изображении"""
        if not self.client:
            return {"error": "Vision API не инициализирован"}
        
        try:
            image = vision.Image(content=image_content)
            
            # Детектирование объектов
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            # Детектирование текста (для этикеток)
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            
            # Детектирование лейблов (общая классификация)
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            
            detected_food = []
            
            # Список пищевых продуктов для фильтрации
            food_keywords = [
                'apple', 'banana', 'orange', 'fruit', 'vegetable', 'bread', 'pasta', 
                'rice', 'pizza', 'burger', 'sandwich', 'salad', 'soup', 'egg', 
                'chicken', 'meat', 'beef', 'pork', 'fish', 'seafood', 'milk', 
                'cheese', 'yogurt', 'ice cream', 'cake', 'cookie', 'chocolate',
                'coffee', 'tea', 'juice', 'water', 'wine', 'beer', 'potato',
                'tomato', 'carrot', 'onion', 'garlic', 'pepper', 'cucumber'
            ]
            
            # Анализ объектов
            for obj in objects:
                if obj.score > 0.5:  # Уверенность > 50%
                    obj_name = obj.name.lower()
                    if any(food in obj_name for food in food_keywords):
                        detected_food.append({
                            'name': obj.name,
                            'confidence': obj.score,
                            'type': 'object'
                        })
            
            # Анализ лейблов
            for label in labels:
                if label.score > 0.7:  # Высокая уверенность
                    label_name = label.description.lower()
                    if any(food in label_name for food in food_keywords):
                        detected_food.append({
                            'name': label.description,
                            'confidence': label.score,
                            'type': 'label'
                        })
            
            # Анализ текста (может содержать названия продуктов)
            if texts:
                full_text = texts[0].description.lower()
                for food in food_keywords:
                    if food in full_text:
                        detected_food.append({
                            'name': food.title(),
                            'confidence': 0.8,
                            'type': 'text'
                        })
            
            # Убираем дубликаты
            unique_food = []
            seen_names = set()
            for item in detected_food:
                if item['name'] not in seen_names:
                    unique_food.append(item)
                    seen_names.add(item['name'])
            
            return {
                'success': True,
                'detected_items': unique_food,
                'total_detected': len(unique_food)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return {"error": str(e)}
    
    def analyze_image(self, image_content):
        """Основной метод анализа изображения"""
        return self.detect_food_items(image_content)

# Создаем экземпляр API
vision_api = VisionAPI('google_vision_credentials.json')
