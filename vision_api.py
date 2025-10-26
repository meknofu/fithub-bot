from google.cloud import vision
import io
import logging
import json
import os
import random
from config import Config
import math

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
            
            # Собираем все продукты с информацией о размере
            for obj in objects:
                if self._is_food_item(obj.name) and obj.score > 0.5:
                    # Рассчитываем относительный размер объекта
                    bounding_poly = obj.bounding_poly
                    if bounding_poly.normalized_vertices:
                        width = abs(bounding_poly.normalized_vertices[1].x - bounding_poly.normalized_vertices[0].x)
                        height = abs(bounding_poly.normalized_vertices[2].y - bounding_poly.normalized_vertices[0].y)
                        area = width * height
                    else:
                        area = 0.1  # значение по умолчанию
                    
                    all_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.2,
                        'area': area,
                        'bounding_box': bounding_poly
                    })
            
            for label in labels:
                if self._is_food_item(label.description) and label.score > 0.6:
                    all_items.append({
                        'name': label.description,
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score,
                        'area': 0.1,  # для labels нет информации о размере
                        'bounding_box': None
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
                'score': best_burger['score'],
                'area': best_burger.get('area', 0.15)
            })
        # Или создаем бургер из компонентов
        elif component_items:
            best_component = max(component_items, key=lambda x: x['score'])
            # Для компонентов увеличиваем предполагаемую площадь
            final_items.append({
                'name': 'бургер',
                'confidence': best_component['confidence'],
                'type': 'burger_inferred',
                'score': best_component['score'],
                'area': best_component.get('area', 0.15) * 1.5
            })
        
        # Добавляем картошку фри если есть
        fries_items = [item for item in items if any(kw in item['name'].lower() for kw in ['fries', 'фри', 'картофель'])]
        if fries_items:
            best_fries = max(fries_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'картофель фри',
                'confidence': best_fries['confidence'],
                'type': 'fries',
                'score': best_fries['score'],
                'area': best_fries.get('area', 0.08)
            })
        
        # Добавляем напиток если есть
        drink_items = [item for item in items if any(kw in item['name'].lower() for kw in ['drink', 'напиток', 'cola', 'кофе', 'cup', 'стакан', 'бутылка'])]
        if drink_items and len(final_items) < 3:
            best_drink = max(drink_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'напиток',
                'confidence': best_drink['confidence'],
                'type': 'drink',
                'score': best_drink['score'],
                'area': best_drink.get('area', 0.05)
            })
        
        # НЕ добавляем общие категории фастфуда если уже есть конкретные продукты
        if not final_items and general_items:
            best_general = max(general_items, key=lambda x: x['score'])
            final_items.append({
                'name': 'фастфуд',
                'confidence': best_general['confidence'],
                'type': 'fast_food',
                'score': best_general['score'],
                'area': best_general.get('area', 0.1)
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
                    'score': item['score'],
                    'area': item.get('area', 0.1)
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
            'drink', 'напиток', 'coffee', 'кофе', 'soup', 'суп', 'salad', 'салат',
            'rice', 'рис', 'pasta', 'паста', 'noodle', 'лапша', 'egg', 'яйцо',
            'cake', 'торт', 'dessert', 'десерт', 'ice cream', 'мороженое'
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
        """Улучшенная оценка веса на основе типа еды и размера на фото"""
        estimated_weights = {}
        
        for item in food_items:
            name = item['name'].lower()
            area = item.get('area', 0.1)  # относительная площадь объекта (0-1)
            
            # Базовый вес в зависимости от типа еды
            base_weights = {
                'бургер': 250,
                'картофель фри': 150,
                'напиток': 330,
                'фастфуд': 300,
                'пицца': 350,
                'сэндвич': 200,
                'салат': 200,
                'суп': 300,
                'курица': 150,
                'рыба': 200,
                'мясо': 200,
                'рис': 150,
                'паста': 200,
                'овощи': 150,
                'фрукты': 150,
                'хлеб': 100,
                'сыр': 100,
                'десерт': 150,
                'мороженое': 100
            }
            
            # Находим подходящий базовый вес
            base_weight = 200  # значение по умолчанию
            for food_type, weight in base_weights.items():
                if food_type in name:
                    base_weight = weight
                    break
            
            # Корректируем вес на основе размера объекта
            # area обычно от 0.01 (маленький объект) до 0.5 (большой объект)
            size_multiplier = self._calculate_size_multiplier(area)
            
            # Дополнительные корректировки для специфичных типов
            type_multiplier = self._get_type_multiplier(name)
            
            estimated_weight = base_weight * size_multiplier * type_multiplier
            
            # Ограничиваем разумными пределами
            estimated_weight = max(50, min(estimated_weight, 1000))
            
            estimated_weights[name] = round(estimated_weight)
        
        return estimated_weights

    def _calculate_size_multiplier(self, area):
        """Рассчитывает множитель размера на основе площади объекта"""
        if area < 0.05:
            return 0.5   # Очень маленький объект
        elif area < 0.1:
            return 0.7   # Маленький объект
        elif area < 0.2:
            return 1.0   # Средний объект
        elif area < 0.3:
            return 1.3   # Большой объект
        else:
            return 1.6   # Очень большой объект

    def _get_type_multiplier(self, food_name):
        """Дополнительные корректировки для специфичных типов еды"""
        if any(word in food_name for word in ['напиток', 'drink', 'кофе', 'чай', 'сок']):
            return 1.0  # Напитки - стандартный расчет
        
        elif any(word in food_name for word in ['салат', 'суп', 'овощ', 'фрукт']):
            return 1.2  # Объемные продукты с низкой плотностью
        
        elif any(word in food_name for word in ['бургер', 'пицца', 'сэндвич']):
            return 1.1  # Комплексные блюда
        
        elif any(word in food_name for word in ['сыр', 'хлеб', 'десерт']):
            return 0.9  # Плотные продукты
        
        else:
            return 1.0  # Стандартный множитель
