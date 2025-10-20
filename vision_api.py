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
        """Определяет все компоненты блюда без дубликатов"""
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
            
            # Сначала объекты (самые точные)
            for obj in objects:
                if self._is_specific_food_item(obj.name) and obj.score > 0.7:
                    normalized_name = self._normalize_food_name(obj.name)
                    if not self._is_duplicate(normalized_name, food_items):
                        food_items.append({
                            'name': normalized_name,
                            'confidence': obj.score,
                            'type': 'object',
                            'score': obj.score + 0.3  # Повышаем вес объектов
                        })
            
            # Затем лейблы (дополняем объекты)
            for label in labels:
                if (self._is_specific_food_item(label.description) and 
                    label.score > 0.8 and
                    not self._is_general_category(label.description)):
                    
                    normalized_name = self._normalize_food_name(label.description)
                    if not self._is_duplicate(normalized_name, food_items):
                        food_items.append({
                            'name': normalized_name,
                            'confidence': label.score,
                            'type': 'label',
                            'score': label.score
                        })
            
            # Сортируем по уверенности и ограничиваем разумным количеством
            food_items.sort(key=lambda x: x['score'], reverse=True)
            food_items = food_items[:4]  # Максимум 4 разных компонента
            
            # Если нашли только общие категории, используем fallback
            if all(self._is_general_category(item['name']) for item in food_items):
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

    def _normalize_food_name(self, food_name):
        """Нормализует название еды, группируя синонимы"""
        food_name_lower = food_name.lower()
        
        # Группируем только настоящие синонимы, а не разные продукты
        food_groups = {
            # Бургеры
            'бургер': ['гамбургер', 'чизбургер', 'hamburger', 'cheeseburger'],
            # Картофель
            'картофель фри': ['фри', 'френч фри', 'french fries', 'fries'],
            'картофель': ['potato', 'картошка'],
            # Напитки
            'кола': ['coca-cola', 'coke', 'пепси', 'pepsi'],
            'напиток': ['drink', 'beverage'],
            # Соусы
            'кетчуп': ['ketchup'],
            'майонез': ['mayonnaise', 'mayo'],
            # Общие группировки (осторожно!)
            'булка': ['bun', 'bread roll'],
        }
        
        # Сначала проверяем точные совпадения
        for main_name, variants in food_groups.items():
            if any(variant == food_name_lower for variant in [main_name] + variants):
                return main_name
        
        # Затем проверяем частичные совпадения (только для явных синонимов)
        for main_name, variants in food_groups.items():
            if any(variant in food_name_lower for variant in variants):
                return main_name
            if main_name in food_name_lower:
                return main_name
        
        return food_name_lower

    def _is_duplicate(self, food_name, existing_items):
        """Проверяет, является ли продукт дубликатом (только для реальных синонимов)"""
        for item in existing_items:
            # Если названия полностью совпадают
            if item['name'] == food_name:
                return True
            
            # Проверяем только явные синонимы, а не разные продукты
            synonyms = {
                'бургер': ['гамбургер', 'чизбургер'],
                'картофель фри': ['фри', 'френч фри'],
                'кола': ['coca-cola', 'пепси'],
            }
            
            for main_name, syn_list in synonyms.items():
                if food_name == main_name and item['name'] in syn_list:
                    return True
                if item['name'] == main_name and food_name in syn_list:
                    return True
            
            # Не считаем дубликатами разные продукты, даже если они похожи
            # Например: "бургер" и "булка" - это разные компоненты
        
        return False

    def _is_specific_food_item(self, item_name):
        """Проверяет, является ли объект конкретной едой"""
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
            # Готовые блюда и компоненты
            'pizza', 'burger', 'sandwich', 'pasta', 'rice', 'sushi',
            'soup', 'salad', 'omelette', 'curry', 'fries', 'french fries',
            # Молочные продукты
            'cheese', 'milk', 'yogurt', 'butter', 'egg', 'eggs',
            # Прочее
            'bread', 'bun', 'cake', 'cookie', 'chocolate', 'ice cream', 
            'coffee', 'cola', 'ketchup', 'mayonnaise', 'sauce'
        ]
        
        item_lower = item_name.lower()
        return any(food in item_lower for food in specific_foods)

    def _is_general_category(self, item_name):
        """Фильтрует только самые общие категории"""
        general_categories = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient', 'produce',
            'fast food', 'junk food', 'snack food'
        ]
        
        item_lower = item_name.lower()
        return any(category == item_lower for category in general_categories)

    def _get_fallback_response(self):
        """Fallback - просим ввести название вручную"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Оценка веса для разных компонентов блюда"""
        estimated_weights = {}
        
        detailed_weight_estimates = {
            # Основные блюда
            'бургер': 200, 'гамбургер': 200, 'чизбургер': 220,
            'пицца': 300, 'сэндвич': 180, 'паста': 250,
            # Гарниры
            'картофель фри': 150, 'фри': 150, 'френч фри': 150,
            'рис': 150, 'картофель': 200, 'картошка': 200,
            'салат': 150, 'овощи': 150,
            # Мясо и рыба
            'курица': 150, 'говядина': 150, 'рыба': 150,
            'свинина': 150, 'стейк': 200,
            # Добавки и соусы
            'сыр': 30, 'соус': 20, 'кетчуп': 20, 'майонез': 15,
            'булка': 50, 'хлеб': 40,
            # Напитки
            'кола': 330, 'напиток': 250, 'кофе': 200,
            # Десерты
            'мороженое': 100, 'торт': 120, 'печенье': 30,
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
            
            # Если не нашли, используем категориальный подход
            if not found_weight:
                if any(word in item_name for word in ['бургер', 'пицца', 'сэндвич']):
                    estimated_weights[item_name] = 200
                elif any(word in item_name for word in ['фри', 'картофель', 'гарнир']):
                    estimated_weights[item_name] = 150
                elif any(word in item_name for word in ['салат', 'овощ']):
                    estimated_weights[item_name] = 150
                elif any(word in item_name for word in ['соус', 'кетчуп', 'майонез']):
                    estimated_weights[item_name] = 20
                elif any(word in item_name for word in ['напиток', 'кола', 'кофе']):
                    estimated_weights[item_name] = 250
                else:
                    estimated_weights[item_name] = 100  # Средний вес по умолчанию
                
        return estimated_weights
