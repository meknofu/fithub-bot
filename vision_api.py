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
        """Умное распознавание с улучшенной группировкой бургеров"""
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
            
            # Собираем все продукты
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
            
            # Умная группировка для бургеров и фастфуда
            food_items = self._smart_burger_grouping(all_items)
            
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

    def _smart_burger_grouping(self, items):
        """Умная группировка для бургеров и фастфуда"""
        if not items:
            return []
        
        items.sort(key=lambda x: x['score'], reverse=True)
        
        # Определяем, есть ли бургер на фото
        has_burger = any('бургер' in item['name'].lower() or 'burger' in item['name'].lower() for item in items)
        has_burger_components = any(comp in item['name'].lower() for item in items for comp in ['bun', 'bread', 'булка', 'котлета', 'patty'])
        
        # Если есть бургер или его компоненты, применяем специальную логику
        if has_burger or has_burger_components:
            return self._group_burger_items(items)
        else:
            return self._remove_duplicates_and_general(items)

    def _group_burger_items(self, items):
        """Группирует компоненты бургера в один продукт"""
        burger_keywords = [
            'бургер', 'burger', 'гамбургер', 'чизбургер', 'hamburger', 'cheeseburger'
        ]
        
        burger_component_keywords = [
            'bun', 'bread', 'булка', 'булочка', 'patty', 'котлета', 
            'beef', 'говядина', 'cheese', 'сыр', 'lettuce', 'салат',
            'tomato', 'помидор', 'onion', 'лук', 'sauce', 'соус'
        ]
        
        general_fast_food = [
            'fast food', 'finger food', 'junk food', 'фастфуд'
        ]
        
        # Находим самый уверенный бургер
        burger_items = [item for item in items if any(kw in item['name'].lower() for kw in burger_keywords)]
        component_items = [item for item in items if any(kw in item['name'].lower() for kw in burger_component_keywords)]
        general_items = [item for item in items if any(kw in item['name'].lower() for kw in general_fast_food)]
        
        final_items = []
        
        # Добавляем бургер (если нашли)
        if burger_items:
            best_burger = max(burger_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'бургер',
                'confidence': best_burger['confidence'],
                'type': 'burger',
                'score': best_burger['score']
            })
        # Или создаем бургер из компонентов
        elif component_items:
            best_component = max(component_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'бургер',
                'confidence': best_component['confidence'],
                'type': 'burger_inferred',
                'score': best_component['score']
            })
        
        # Добавляем картошку фри если есть
        fries_items = [item for item in items if any(kw in item['name'].lower() for kw in ['fries', 'фри', 'картофель'])]
        if fries_items:
            best_fries = max(fries_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'картофель фри',
                'confidence': best_fries['confidence'],
                'type': 'fries',
                'score': best_fries['score']
            })
        
        # Добавляем напиток если есть
        drink_items = [item for item in items if any(kw in item['name'].lower() for kw in ['drink', 'напиток', 'cola', 'кофе'])]
        if drink_items and len(final_items) < 3:
            best_drink = max(drink_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'напиток',
                'confidence': best_drink['confidence'],
                'type': 'drink',
                'score': best_drink['score']
            })
        
        # НЕ добавляем общие категории фастфуда если уже есть конкретные продукты
        if not final_items and general_items:
            best_general = max(general_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'фастфуд',
                'confidence': best_general['confidence'],
                'type': 'fast_food',
                'score': best_general['score']
            })
        
        return final_items[:3]  # Максимум 3 продукта

    def _remove_duplicates_and_general(self, items):
        """Убирает дубликаты и общие категории для обычной еды"""
        seen_names = set()
        unique_items = []
        
        for item in items:
            original_name = item['name'].lower()
            normalized_name = self._normalize_name(original_name)
            
            # Пропускаем общие категории
            if self._is_general_category(normalized_name):
                continue
                
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_items.append({
                    'name': normalized_name,
                    'confidence': item['confidence'],
                    'type': item['type'],
                    'score': item['score']
                })
        
        return unique_items[:4]

    def _normalize_name(self, name):
        """Нормализует названия"""
        name_lower = name.lower()
        
        exact_synonyms = {
            'гамбургер': 'бургер',
            'чизбургер': 'бургер', 
            'hamburger': 'бургер',
            'cheeseburger': 'бургер',
            'френч фри': 'картофель фри',
            'french fries': 'картофель фри',
            'fries': 'картофель фри',
            'coca-cola': 'кола',
            'coke': 'кола',
            'pepsi': 'кола',
            'пепси': 'кола',
        }
        
        if name_lower in exact_synonyms:
            return exact_synonyms[name_lower]
        
        for original, replacement in exact_synonyms.items():
            if original in name_lower:
                return replacement
        
        return name_lower

    def _is_food_item(self, item_name):
        """Проверяет, является ли объект едой"""
        item_lower = item_name.lower()
        
        food_keywords = [
            'food', 'еда', 'meal', 'блюдо', 'fruit', 'фрукт', 'vegetable', 'овощ',
            'burger', 'бургер', 'pizza', 'пицца', 'sandwich', 'сэндвич', 'fish', 'рыба',
            'meat', 'мясо', 'chicken', 'курица', 'bread', 'хлеб', 'cheese', 'сыр',
            'drink', 'напиток', 'coffee', 'кофе', 'soup', 'суп', 'salad', 'салат'
        ]
        
        return any(keyword in item_lower for keyword in food_keywords)

    def _is_general_category(self, item_name):
        """Фильтрует общие категории"""
        general_categories = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient', 'produce',
            'fast food', 'finger food', 'junk food', 'фастфуд'
        ]
        
        return item_name in general_categories

    def _get_fallback_response(self):
        """Fallback"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Оценка веса"""
        estimated_weights = {}
        
        for item in food_items:
            name = item['name'].lower()
            
            if name == 'бургер':
                estimated_weights[name] = 250
            elif name == 'картофель фри':
                estimated_weights[name] = 150
            elif name == 'напиток':
                estimated_weights[name] = 330
            elif name == 'фастфуд':
                estimated_weights[name] = 300
            elif any(word in name for word in ['салат', 'овощ', 'фрукт']):
                estimated_weights[name] = 150
            else:
                estimated_weights[name] = 200
        
        return estimated_weights
