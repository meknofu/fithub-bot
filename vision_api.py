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
        """Умное определение компонентов блюда с улучшенной группировкой"""
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
            
            raw_items = []
            
            # Собираем все возможные продукты
            for obj in objects:
                if self._is_food_related(obj.name) and obj.score > 0.6:
                    raw_items.append({
                        'name': obj.name.lower(),
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.3
                    })
            
            for label in labels:
                if self._is_food_related(label.description) and label.score > 0.7:
                    raw_items.append({
                        'name': label.description.lower(),
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score
                    })
            
            # Применяем умную группировку
            food_items = self._smart_grouping(raw_items)
            
            # Ограничиваем количество и фильтруем общие категории
            food_items = [item for item in food_items if not self._is_general_category(item['name'])]
            food_items = food_items[:3]  # Максимум 3 основных компонента
            
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

    def _smart_grouping(self, raw_items):
        """Умная группировка продуктов по категориям"""
        if not raw_items:
            return []
        
        # Сортируем по уверенности
        raw_items.sort(key=lambda x: x['score'], reverse=True)
        
        categories = {
            'burger': [],
            'fries': [], 
            'drink': [],
            'sauce': [],
            'other': []
        }
        
        # Распределяем по категориям
        for item in raw_items:
            name = item['name']
            
            if any(word in name for word in ['burger', 'бургер', 'гамбургер', 'чизбургер', 'буффало']):
                categories['burger'].append(item)
            elif any(word in name for word in ['fries', 'фри', 'картофель', 'potato']):
                categories['fries'].append(item)
            elif any(word in name for word in ['drink', 'cola', 'напиток', 'coffee', ' beverage']):
                categories['drink'].append(item)
            elif any(word in name for word in ['sauce', 'соус', 'кетчуп', 'майонез', 'ketchup']):
                categories['sauce'].append(item)
            else:
                categories['other'].append(item)
        
        # Выбираем лучшие представители из каждой категории
        final_items = []
        
        # Для бургеров - берем только самый уверенный вариант
        if categories['burger']:
            best_burger = max(categories['burger'], key=lambda x: x['score'])
            final_items.append({
                'name': 'бургер',
                'confidence': best_burger['confidence'],
                'type': 'grouped',
                'score': best_burger['score']
            })
        
        # Для картошки фри
        if categories['fries']:
            best_fries = max(categories['fries'], key=lambda x: x['score'])
            final_items.append({
                'name': 'картофель фри', 
                'confidence': best_fries['confidence'],
                'type': 'grouped',
                'score': best_fries['score']
            })
        
        # Для напитков
        if categories['drink']:
            best_drink = max(categories['drink'], key=lambda x: x['score'])
            final_items.append({
                'name': 'напиток',
                'confidence': best_drink['confidence'], 
                'type': 'grouped',
                'score': best_drink['score']
            })
        
        # Для соусов (только если нет других компонентов)
        if categories['sauce'] and len(final_items) < 2:
            best_sauce = max(categories['sauce'], key=lambda x: x['score'])
            final_items.append({
                'name': 'соус',
                'confidence': best_sauce['confidence'],
                'type': 'grouped', 
                'score': best_sauce['score']
            })
        
        # Добавляем другие продукты, если места есть
        if categories['other'] and len(final_items) < 3:
            for item in categories['other'][:3-len(final_items)]:
                # Не добавляем компоненты, которые уже есть в основных категориях
                if not any(word in item['name'] for word in ['bread', 'bun', 'булка', 'булочка', 'сыр', 'cheese']):
                    final_items.append(item)
        
        # Если нашли только компоненты бургера, но не сам бургер
        burger_components = [item for item in final_items if any(word in item['name'] for word in ['bun', 'bread', 'булка', 'котлета'])]
        if burger_components and not any('бургер' in item['name'] for item in final_items):
            # Заменяем компоненты на общий бургер
            final_items = [item for item in final_items if item not in burger_components]
            best_component = max(burger_components, key=lambda x: x['score'])
            final_items.append({
                'name': 'бургер',
                'confidence': best_component['confidence'],
                'type': 'inferred',
                'score': best_component['score']
            })
        
        return final_items

    def _is_food_related(self, item_name):
        """Проверяет, относится ли объект к еде"""
        item_lower = item_name.lower()
        
        food_keywords = [
            # Основные блюда
            'burger', 'бургер', 'pizza', 'пицца', 'sandwich', 'сэндвич',
            'fries', 'фри', 'potato', 'картофель', 'chicken', 'курица',
            'beef', 'говядина', 'fish', 'рыба', 'pasta', 'паста', 'rice', 'рис',
            # Компоненты
            'bread', 'bun', 'булка', 'cheese', 'сыр', 'sauce', 'соус',
            'vegetable', 'овощ', 'salad', 'салат', 'tomato', 'помидор',
            # Напитки
            'drink', 'beverage', 'напиток', 'cola', 'кофе', 'coffee',
            # Общие
            'food', 'еда', 'meal', 'блюдо'
        ]
        
        return any(keyword in item_lower for keyword in food_keywords)

    def _is_general_category(self, item_name):
        """Фильтрует общие категории"""
        general_categories = [
            'food', 'cuisine', 'meal', 'dish', 'fast food', 'junk food'
        ]
        
        return item_name.lower() in general_categories

    def _get_fallback_response(self):
        """Fallback - просим ввести название вручную"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Оценка веса для сгруппированных продуктов"""
        estimated_weights = {}
        
        weight_estimates = {
            # Основные блюда
            'бургер': 250,
            'картофель фри': 150,
            'пицца': 300,
            'сэндвич': 200,
            'курица': 180,
            'рыба': 200,
            # Гарниры
            'рис': 150,
            'паста': 200,
            'салат': 150,
            'овощи': 150,
            # Напитки
            'напиток': 330,
            'кола': 330,
            'кофе': 200,
            # Добавки
            'соус': 30,
            'сыр': 20
        }
        
        for item in food_items:
            item_name = item['name'].lower()
            
            # Ищем точное совпадение
            found = False
            for food, weight in weight_estimates.items():
                if food in item_name:
                    estimated_weights[item_name] = weight
                    found = True
                    break
            
            # Если не нашли, используем логику
            if not found:
                if any(word in item_name for word in ['бургер', 'пицца', 'сэндвич']):
                    estimated_weights[item_name] = 250
                elif any(word in item_name for word in ['фри', 'картофель']):
                    estimated_weights[item_name] = 150
                elif any(word in item_name for word in ['напиток', 'кола', 'кофе']):
                    estimated_weights[item_name] = 330
                else:
                    estimated_weights[item_name] = 100
        
        return estimated_weights
