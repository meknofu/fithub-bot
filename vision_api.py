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
        """Улучшенное распознавание с акцентом на рыбу и морепродукты"""
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
            
            # Собираем все возможные продукты с более низким порогом
            for obj in objects:
                if self._is_food_related(obj.name) and obj.score > 0.5:
                    raw_items.append({
                        'name': obj.name.lower(),
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.3
                    })
            
            for label in labels:
                if self._is_food_related(label.description) and label.score > 0.6:
                    raw_items.append({
                        'name': label.description.lower(),
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score
                    })
            
            # Применяем улучшенную группировку
            food_items = self._enhanced_grouping(raw_items)
            
            # Менее агрессивная фильтрация
            food_items = [item for item in food_items if not self._is_too_general(item['name'])]
            food_items = food_items[:4]  # До 4 компонентов
            
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

    def _enhanced_grouping(self, raw_items):
        """Улучшенная группировка с акцентом на рыбу"""
        if not raw_items:
            return []
        
        # Сортируем по уверенности
        raw_items.sort(key=lambda x: x['score'], reverse=True)
        
        categories = {
            'fish': [],
            'seafood': [],
            'vegetable': [],
            'meat': [],
            'burger': [],
            'fries': [], 
            'other': []
        }
        
        # Распределяем по расширенным категориям
        for item in raw_items:
            name = item['name']
            
            # Рыба и морепродукты (расширенный список)
            if any(word in name for word in ['fish', 'рыба', 'salmon', 'лосось', 'tuna', 'тунец', 
                                           'trout', 'форель', 'seabass', 'сибас', 'carp', 'карп',
                                           'herring', 'сельдь', 'mackerel', 'скумбрия', 'cod', 'треска']):
                categories['fish'].append(item)
            elif any(word in name for word in ['seafood', 'морепродукт', 'shrimp', 'креветка', 'crab', 'краб',
                                             'lobster', 'омар', 'mussel', 'мидия', 'oyster', 'устрица']):
                categories['seafood'].append(item)
            elif any(word in name for word in ['vegetable', 'овощ', 'salad', 'салат', 'tomato', 'помидор',
                                             'cucumber', 'огурец', 'carrot', 'морковь', 'potato', 'картофель']):
                categories['vegetable'].append(item)
            elif any(word in name for word in ['burger', 'бургер']):
                categories['burger'].append(item)
            elif any(word in name for word in ['fries', 'фри']):
                categories['fries'].append(item)
            elif any(word in name for word in ['meat', 'мясо', 'chicken', 'курица', 'beef', 'говядина']):
                categories['meat'].append(item)
            else:
                categories['other'].append(item)
        
        # Выбираем лучшие представители из каждой категории
        final_items = []
        
        # Приоритет: рыба и морепродукты
        if categories['fish']:
            best_fish = max(categories['fish'], key=lambda x: x['score'])
            # Определяем конкретный тип рыбы если возможно
            fish_name = self._determine_fish_type(best_fish['name'])
            final_items.append({
                'name': fish_name,
                'confidence': best_fish['confidence'],
                'type': 'fish',
                'score': best_fish['score']
            })
        
        if categories['seafood'] and len(final_items) < 3:
            best_seafood = max(categories['seafood'], key=lambda x: x['score'])
            final_items.append({
                'name': 'морепродукты',
                'confidence': best_seafood['confidence'],
                'type': 'seafood',
                'score': best_seafood['score']
            })
        
        # Овощи (только если есть место и они не доминируют)
        if categories['vegetable'] and len(final_items) < 3:
            # Если уже есть рыба/мясо, добавляем овощи как гарнир
            if any(cat in [item['type'] for item in final_items] for cat in ['fish', 'seafood', 'meat']):
                best_veg = max(categories['vegetable'], key=lambda x: x['score'])
                final_items.append({
                    'name': self._determine_vegetable_type(best_veg['name']),
                    'confidence': best_veg['confidence'],
                    'type': 'vegetable',
                    'score': best_veg['score']
                })
        
        # Мясо (если нет рыбы)
        if not categories['fish'] and categories['meat'] and len(final_items) < 3:
            best_meat = max(categories['meat'], key=lambda x: x['score'])
            final_items.append({
                'name': self._determine_meat_type(best_meat['name']),
                'confidence': best_meat['confidence'],
                'type': 'meat',
                'score': best_meat['score']
            })
        
        # Другие категории
        if categories['burger'] and len(final_items) < 2:
            best_burger = max(categories['burger'], key=lambda x: x['score'])
            final_items.append({
                'name': 'бургер',
                'confidence': best_burger['confidence'],
                'type': 'burger',
                'score': best_burger['score']
            })
        
        if categories['fries'] and len(final_items) < 3:
            best_fries = max(categories['fries'], key=lambda x: x['score'])
            final_items.append({
                'name': 'картофель фри',
                'confidence': best_fries['confidence'],
                'type': 'fries',
                'score': best_fries['score']
            })
        
        # Добавляем другие продукты если места есть
        if categories['other'] and len(final_items) < 3:
            for item in categories['other'][:3-len(final_items)]:
                # Фильтруем слишком общие категории
                if not self._is_too_general(item['name']):
                    final_items.append(item)
        
        return final_items

    def _determine_fish_type(self, fish_name):
        """Определяет конкретный тип рыбы"""
        fish_mapping = {
            'salmon': 'лосось',
            'лосось': 'лосось',
            'tuna': 'тунец', 
            'тунец': 'тунец',
            'trout': 'форель',
            'форель': 'форель',
            'seabass': 'сибас',
            'сибас': 'сибас',
            'carp': 'карп',
            'карп': 'карп',
            'cod': 'треска',
            'треска': 'треска'
        }
        
        for eng, rus in fish_mapping.items():
            if eng in fish_name:
                return rus
        
        return 'рыба'  # Общее название по умолчанию

    def _determine_vegetable_type(self, veg_name):
        """Определяет конкретный тип овощей"""
        veg_mapping = {
            'tomato': 'помидоры',
            'помидор': 'помидоры',
            'cucumber': 'огурцы',
            'огурец': 'огурцы',
            'carrot': 'морковь',
            'морковь': 'морковь',
            'potato': 'картофель',
            'картофель': 'картофель',
            'salad': 'салат',
            'салат': 'салат'
        }
        
        for eng, rus in veg_mapping.items():
            if eng in veg_name:
                return rus
        
        return 'овощи'

    def _determine_meat_type(self, meat_name):
        """Определяет конкретный тип мяса"""
        meat_mapping = {
            'chicken': 'курица',
            'курица': 'курица',
            'beef': 'говядина',
            'говядина': 'говядина',
            'pork': 'свинина',
            'свинина': 'свинина'
        }
        
        for eng, rus in meat_mapping.items():
            if eng in meat_name:
                return rus
        
        return 'мясо'

    def _is_food_related(self, item_name):
        """Расширенный список ключевых слов для еды"""
        item_lower = item_name.lower()
        
        food_keywords = [
            # Рыба и морепродукты
            'fish', 'рыба', 'salmon', 'лосось', 'tuna', 'тунец', 'trout', 'форель',
            'seabass', 'сибас', 'carp', 'карп', 'herring', 'сельдь', 'mackerel', 'скумбрия',
            'cod', 'треска', 'seafood', 'морепродукт', 'shrimp', 'креветка', 'crab', 'краб',
            'lobster', 'омар', 'mussel', 'мидия', 'oyster', 'устрица',
            # Мясо и птица
            'meat', 'мясо', 'chicken', 'курица', 'beef', 'говядина', 'pork', 'свинина',
            'steak', 'стейк', 'sausage', 'колбаса', 'bacon', 'бекон',
            # Овощи
            'vegetable', 'овощ', 'salad', 'салат', 'tomato', 'помидор', 'cucumber', 'огурец',
            'carrot', 'морковь', 'potato', 'картофель', 'onion', 'лук', 'pepper', 'перец',
            'broccoli', 'брокколи', 'cabbage', 'капуста', 'lettuce', 'латук',
            # Фрукты
            'fruit', 'фрукт', 'apple', 'яблоко', 'banana', 'банан', 'orange', 'апельсин',
            # Основные блюда
            'burger', 'бургер', 'pizza', 'пицца', 'sandwich', 'сэндвич', 'pasta', 'паста',
            'rice', 'рис', 'soup', 'суп', 'curry', 'карри',
            # Общие
            'food', 'еда', 'meal', 'блюдо', 'dish'
        ]
        
        return any(keyword in item_lower for keyword in food_keywords)

    def _is_too_general(self, item_name):
        """Фильтрует только самые общие категории"""
        too_general = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient'
        ]
        
        return item_name.lower() in too_general

    def _get_fallback_response(self):
        """Fallback - просим ввести название вручную"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {}
        }

    def estimate_weights(self, food_items):
        """Оценка веса с учетом типа продукта"""
        estimated_weights = {}
        
        weight_estimates = {
            # Рыба
            'рыба': 150, 'лосось': 150, 'тунец': 150, 'форель': 150,
            'сибас': 200, 'карп': 200, 'треска': 150,
            # Морепродукты
            'морепродукты': 100, 'креветки': 100, 'краб': 150,
            # Мясо
            'курица': 150, 'говядина': 200, 'свинина': 150, 'мясо': 150,
            # Овощи
            'овощи': 150, 'помидоры': 100, 'огурцы': 100, 'морковь': 100,
            'картофель': 200, 'салат': 100,
            # Другое
            'бургер': 250, 'картофель фри': 150
        }
        
        for item in food_items:
            item_name = item['name'].lower()
            
            found = False
            for food, weight in weight_estimates.items():
                if food in item_name:
                    estimated_weights[item_name] = weight
                    found = True
                    break
            
            if not found:
                if item['type'] == 'fish':
                    estimated_weights[item_name] = 150
                elif item['type'] == 'vegetable':
                    estimated_weights[item_name] = 100
                elif item['type'] == 'meat':
                    estimated_weights[item_name] = 150
                else:
                    estimated_weights[item_name] = 100
        
        return estimated_weights
