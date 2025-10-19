import os
import base64
import logging
from google.cloud import vision
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self, credentials_path=None):
        if credentials_path and os.path.exists(credentials_path):
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = vision.ImageAnnotatorClient(credentials=self.credentials)
        else:
            # Попробуем использовать переменные окружения
            try:
                self.client = vision.ImageAnnotatorClient()
            except Exception as e:
                logger.error(f"Failed to initialize Vision API: {e}")
                self.client = None
    
    def analyze_image(self, image_content):
        """Анализ изображения и определение объектов"""
        if not self.client:
            return {"error": "Vision API not initialized"}
        
        try:
            image = vision.Image(content=image_content)
            
            # Определение объектов на изображении
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            # Определение текста (если есть этикетки)
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            
            detected_items = []
            
            # Анализ объектов
            for obj in objects:
                if obj.score > 0.5:  # Минимальная уверенность 50%
                    detected_items.append({
                        'name': obj.name.lower(),
                        'confidence': obj.score,
                        'type': 'object'
                    })
            
            # Анализ текста (может содержать названия продуктов)
            if texts:
                text_description = texts[0].description.lower()
                # Ищем ключевые слова, связанные с едой
                food_keywords = [
                    'apple', 'banana', 'bread', 'rice', 'pasta', 'chicken', 'meat',
                    'fish', 'egg', 'milk', 'cheese', 'yogurt', 'vegetable', 'fruit',
                    'potato', 'tomato', 'salad', 'soup', 'sandwich', 'pizza'
                ]
                
                for keyword in food_keywords:
                    if keyword in text_description:
                        detected_items.append({
                            'name': keyword,
                            'confidence': 0.7,
                            'type': 'text'
                        })
            
            # Убираем дубликаты
            unique_items = []
            seen_names = set()
            for item in detected_items:
                if item['name'] not in seen_names:
                    unique_items.append(item)
                    seen_names.add(item['name'])
            
            return {
                'success': True,
                'detected_items': unique_items,
                'count': len(unique_items)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return {"error": str(e)}

# Глобальный экземпляр Vision API
vision_api = VisionAPI()
