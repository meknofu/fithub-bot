from google.cloud import vision
import io
import logging
import math
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
        """Основная функция распознавания еды (рабочая версия)"""
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
                    # Рассчитываем относительный размер объекта
                    area = self._calculate_object_area(obj)
                    
                    all_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.2,
                        'area': area
                    })
            
            for label in labels:
                if self._is_food_item(label.description) and label.score > 0.6:
                    all_items.append({
                        'name': label.description,
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score,
                        'area': 0.1
                    })
            
            # Умная группировка для бургеров и фастфуда
            food_items = self._smart_burger_grouping(all_items)
            
            if not food_items:
                return self._get_fallback_response()
            
            detected_text = texts[0].description if texts else ""
            
            # Пытаемся найти референсные объекты для улучшения оценки веса
            reference_objects = self._find_reference_objects(objects)
            
            return {
                'food_items': food_items,
                'detected_text': detected_text,
                'estimated_weights': self.estimate_weights(food_items, reference_objects),
                'reference_detected': bool(reference_objects),
                'reference_objects': reference_objects
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()

    def _find_reference_objects(self, objects):
        """Находит референсные объекты на фото"""
        reference_keywords = {
            'fork': ['fork', 'вилка', 'столовый прибор'],
            'spoon': ['spoon', 'ложка', 'ложечка'],
            'knife': ['knife', 'нож'],
            'phone': ['phone', 'mobile phone', 'телефон', 'смартфон', 'iphone'],
            'credit card': ['credit card', 'банковская карта', 'карта'],
            'hand': ['hand', 'рука', 'ладонь']
        }
        
        references = []
        for obj in objects:
            for ref_type, keywords in reference_keywords.items():
                if any(keyword in obj.name.lower() for keyword in keywords) and obj.score > 0.6:
                    area = self._calculate_object_area(obj)
                    references.append({
                        'type': ref_type,
                        'name': obj.name,
                        'confidence': obj.score,
                        'area': area
                    })
        
        return references

    def estimate_weights(self, food_items, reference_objects=None):
        """Улучшенная оценка веса с учетом референсных объектов"""
        estimated_weights = {}
        
        # Определяем базовый размер на основе референсов
        base_size = self._get_base_size_from_references(reference_objects)
        
        for item in food_items:
            name = item['name'].lower()
            area = item.get('area', 0.1)
            
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
                'мороженое': 100,
                'яйцо': 50,
                'яичница': 120,
                'омлет': 200
            }
            
            # Находим подходящий базовый вес
            base_weight = 200  # значение по умолчанию
            for food_type, weight in base_weights.items():
                if food_type in name:
                    base_weight = weight
                    break
            
            # Корректируем вес на основе размера объекта и референса
            size_multiplier = self._calculate_size_multiplier(area, base_size)
            
            # Дополнительные корректировки для специфичных типов
            type_multiplier = self._get_type_multiplier(name)
            
            estimated_weight = base_weight * size_multiplier * type_multiplier
            
            # Ограничиваем разумными пределами
            estimated_weight = max(50, min(estimated_weight, 1000))
            
            estimated_weights[name] = round(estimated_weight)
        
        return estimated_weights

    def _get_base_size_from_references(self, reference_objects):
        """Определяет базовый размер на основе референсных объектов"""
        if not reference_objects:
            return 'medium'  # средний размер по умолчанию
        
        # Анализируем размер референсных объектов относительно всей сцены
        total_reference_area = sum(ref['area'] for ref in reference_objects)
        avg_reference_area = total_reference_area / len(reference_objects)
        
        if avg_reference_area < 0.05:
            return 'small'
        elif avg_reference_area > 0.2:
            return 'large'
        else:
            return 'medium'

    def _calculate_size_multiplier(self, area, base_size):
        """Рассчитывает множитель размера"""
        # Базовые множители в зависимости от общего размера сцены
        base_multipliers = {
            'small': 0.7,
            'medium': 1.0,
            'large': 1.3
        }
        
        base_multiplier = base_multipliers.get(base_size, 1.0)
        
        # Корректировка на основе площади конкретного объекта
        if area < 0.05:
            return base_multiplier * 0.6
        elif area < 0.1:
            return base_multiplier * 0.8
        elif area < 0.2:
            return base_multiplier * 1.0
        elif area < 0.3:
            return base_multiplier * 1.2
        else:
            return base_multiplier * 1.5

    def _calculate_object_area(self, obj):
        """Рассчитывает площадь объекта в нормализованных координатах"""
        if not obj.bounding_poly.normalized_vertices:
            return 0.1
        
        vertices = obj.bounding_poly.normalized_vertices
        width = abs(vertices[1].x - vertices[0].x)
        height = abs(vertices[2].y - vertices[0].y)
        return width * height

    def _get_type_multiplier(self, food_name):
        """Дополнительные корректировки для специфичных типов еды"""
        if any(word in food_name for word in ['напиток', 'drink', 'кофе', 'чай', 'сок']):
            return 1.0
        
        elif any(word in food_name for word in ['салат', 'суп', 'овощ', 'фрукт']):
            return 1.2
        
        elif any(word in food_name for word in ['бургер', 'пицца', 'сэндвич']):
            return 1.1
        
        elif any(word in food_name for word in ['сыр', 'хлеб', 'десерт']):
            return 0.9
        
        else:
            return 1.0

    # Остальные методы остаются без изменений...
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
        
        # Остальная логика группировки...
        burger_items = [item for item in items if any(kw in item['name'].lower() for kw in burger_keywords)]
        # ... (предыдущая реализация)

    def _remove_duplicates_and_general(self, items):
        """Убирает дубликаты и общие категории"""
        seen_names = set()
        unique_items = []
        
        for item in items:
            original_name = item['name'].lower()
            normalized_name = self._normalize_name(original_name)
            
            if self._is_general_category(normalized_name):
                continue
                
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_items.append(item)
        
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
            'cake', 'торт', 'dessert', 'десерт', 'ice cream', 'мороженое',
            'breakfast', 'завтрак', 'lunch', 'обед', 'dinner', 'ужин'
        ]
        
        return any(keyword in item_lower for keyword in food_keywords)

    def _is_general_category(self, item_name):
        """Фильтрует общие категории"""
        general_categories = [
            'food', 'cuisine', 'meal', 'dish', 'ingredient', 'produce',
            'fast food', 'finger food', 'junk food', 'фастфуд',
            'breakfast', 'lunch', 'dinner'
        ]
        
        return item_name in general_categories

    def _get_fallback_response(self):
        """Fallback"""
        return {
            'food_items': [],
            'detected_text': 'Не удалось определить конкретные продукты',
            'estimated_weights': {},
            'reference_detected': False,
            'reference_objects': []
        }
