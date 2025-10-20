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
        """Упрощенное и более точное распознавание продуктов"""
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
            
            all_items = []
            
            # Собираем ВСЕ продукты с нормальным порогом
            for obj in objects:
                if self._is_food_item(obj.name) and obj.score > 0.5:
                    all_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.2
                    })
            
            for label in labels:
                if self._is_food_item(label.description) and label.score > 0.6:
                    all_items.append({
                        'name': label.description,
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score
                    })
            
            # Убираем только настоящие дубликаты и слишком общие категории
            food_items = self._remove_real_duplicates(all_items)
            
            # Ограничиваем разумным количеством
            food_items = food_items[:4]
            
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

    def _remove_real_duplicates(self, items):
        """Убирает только настоящие дубликаты, сохраняя разные продукты"""
        if not items:
            return []
        
        # Сортируем по уверенности
        items.sort(key=lambda x: x['score'], reverse=True)
        
        seen_names = set()
        unique_items = []
        
        for item in items:
            original_name = item['name'].lower()
            normalized_name = self._normalize_name(original_name)
            
            # Пропускаем слишком общие категории
            if self._is_too_general(normalized_name):
                continue
                
            # Если это РАЗНЫЙ продукт - добавляем
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_items.append({
                    'name': normalized_name,
                    'confidence': item['confidence'],
                    'type': item['type'],
                    'score': item['score']
                })
        
        return unique_items

    def _normalize_name(self, name):
        """Нормализует названия, группируя только настоящие синонимы"""
        name_lower = name.lower()
        
        # Группируем ТОЛЬКО явные синонимы
        exact_synonyms = {
            # Бургеры
            'гамбургер': 'бургер',
            'чизбургер': 'бургер', 
            'hamburger': 'бургер',
            'cheeseburger': 'бургер',
            # Картофель фри
            'френч фри': 'картофель фри',
            'french fries': 'картофель фри',
            'fries': 'картофель фри',
            # Напитки
            'coca-cola': 'кола',
            'coke': 'кола',
            'pepsi': 'кола',
            'пепси': 'кола',
            # Соусы
            'ketchup': 'кетчуп',
            'mayonnaise': 'майонез',
            'mayo': 'майонез',
        }
        
        # Проверяем точные совпадения
        if name_lower in exact_synonyms:
            return exact_synonyms[name_lower]
        
        # Проверяем частичные совпадения только для определенных случаев
        for original, replacement in exact_synonyms.items():
            if original in name_lower:
                return replacement
        
        return name_lower

    def _is_food_item(self, item_name):
        """Проверяет, является ли объект едой (расширенный список)"""
        item_lower = item_name.lower()
        
        food_keywords = [
            # Фрукты и ягоды
            'fruit', 'фрукт', 'apple', 'яблоко', 'banana', 'банан', 'orange', 'апельсин',
            'grape', 'виноград', 'strawberry', 'клубника', 'watermelon', 'арбуз',
            'pineapple', 'ананас', 'mango', 'манго', 'pear', 'груша', 'peach', 'персик',
            'cherry', 'вишня', 'kiwi', 'киви', 'berry', 'ягода',
            # Овощи
            'vegetable', 'овощ', 'tomato', 'помидор', 'cucumber', 'огурец', 'carrot', 'морковь',
            'potato', 'картофель', 'onion', 'лук', 'pepper', 'перец', 'broccoli', 'брокколи',
            'cabbage', 'капуста', 'lettuce', 'салат', 'spinach', 'шпинат', 'corn', 'кукуруза',
            # Рыба и морепродукты
            'fish', 'рыба', 'salmon', 'лосось', 'tuna', 'тунец', 'trout', 'форель',
            'seabass', 'сибас', 'carp', 'карп', 'cod', 'треска', 'seafood', 'морепродукт',
            'shrimp', 'креветка', 'crab', 'краб', 'lobster', 'омар',
            # Мясо и птица
            'meat', 'мясо', 'chicken', 'курица', 'beef', 'говядина', 'pork', 'свинина',
            'steak', 'стейк', 'sausage', 'колбаса', 'bacon', 'бекон', 'turkey', 'индейка',
            # Молочные продукты
            'cheese', 'сыр', 'milk', 'молоко', 'yogurt', 'йогурт', 'butter', 'масло',
            'egg', 'яйцо', 'cream', 'сливки', 'curd', 'творог',
            # Зерновые и крупы
            'bread', 'хлеб', 'pasta', 'паста', 'rice', 'рис', 'cereal', 'хлопья',
            'oatmeal', 'овсянка', 'buckwheat', 'гречка', 'flour', 'мука',
            # Готовые блюда
            'burger', 'бургер', 'pizza', 'пицца', 'sandwich', 'сэндвич', 'soup', 'суп',
            'salad', 'салат', 'omelette', 'омлет', 'curry', 'карри', 'sushi', 'суши',
            # Напитки
            'drink', 'напиток', 'coffee', 'кофе', 'tea', 'чай', 'juice', 'сок',
            'water', 'вода', 'beverage',
            # Сладости и десерты
            'cake', 'торт', 'cookie', 'печенье', 'chocolate', 'шоколад', 'ice cream', 'мороженое',
            'candy', 'конфета', 'dessert', 'десерт',
            # Орехи и семена
            'nut', 'орех', 'almond', 'миндаль', 'walnut', 'грецкий', 'seed', 'семечка',
            # Общие
            'food', 'еда', 'meal', 'блюдо'
        ]
        
        return any(keyword in item_lower for keyword in food_keywords)

    def _is_too_general(self, item_name):
        """Фильтрует только САМЫЕ общие категории"""
        too_general = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient', 'produce'
        ]
        
        return item_name in too_general

    def _get_fallback_response(self):
        """Fallback - просим ввести название вручную"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Простая и понятная оценка веса"""
        estimated_weights = {}
        
        # Базовые веса по типам продуктов
        for item in food_items:
            name = item['name'].lower()
            
            if any(word in name for word in ['бургер', 'пицца', 'сэндвич', 'стейк']):
                estimated_weights[name] = 250
            elif any(word in name for word in ['рыба', 'лосось', 'тунец', 'курица', 'мясо']):
                estimated_weights[name] = 150
            elif any(word in name for word in ['картофель фри', 'фри', 'гарнир']):
                estimated_weights[name] = 150
            elif any(word in name for word in ['салат', 'овощ', 'фрукт']):
                estimated_weights[name] = 100
            elif any(word in name for word in ['суп', 'каша', 'паста']):
                estimated_weights[name] = 300
            elif any(word in name for word in ['напиток', 'кофе', 'чай']):
                estimated_weights[name] = 200
            elif any(word in name for word in ['сыр', 'соус', 'кетчуп']):
                estimated_weights[name] = 30
            else:
                estimated_weights[name] = 100  # Средний вес по умолчанию
        
        return estimated_weights
