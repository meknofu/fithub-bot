from google.cloud import vision
import io
import logging
import math
from config import Config  # ДОБАВЛЯЕМ ЭТОТ ИМПОРТ

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

    # Остальной код остается без изменений...
    def detect_food_items_with_reference(self, image_content, reference_object=None):
        """Распознавание еды с учетом референсного объекта"""
        if not self.client:
            return self._get_fallback_response()
            
        try:
            image = vision.Image(content=image_content)
            
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            # Ищем референсные объекты
            reference_objects = self._find_reference_objects(objects)
            
            # Если пользователь указал референсный объект, используем его
            if reference_object:
                reference_size = self._get_reference_size(reference_object)
            else:
                # Пытаемся автоматически определить референс
                reference_size = self._auto_detect_reference(reference_objects)
            
            all_items = []
            
            for obj in objects:
                if self._is_food_item(obj.name) and obj.score > 0.5:
                    area = self._calculate_object_area(obj)
                    
                    all_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.2,
                        'area': area,
                        'bounding_box': obj.bounding_poly,
                        'estimated_weight': self._estimate_weight_with_reference(
                            obj.name, area, reference_size
                        )
                    })
            
            # Умная группировка
            food_items = self._smart_burger_grouping(all_items)
            
            return {
                'food_items': food_items,
                'reference_detected': bool(reference_objects),
                'reference_objects': reference_objects,
                'estimated_weights': {item['name']: item['estimated_weight'] for item in food_items}
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

    def _get_reference_size(self, reference_type):
        """Возвращает реальный размер референсного объекта в см²"""
        reference_sizes = {
            'fork': (25, 3),  # длина 25см, ширина 3см
            'spoon': (20, 4),  # длина 20см, ширина 4см
            'knife': (25, 3),  # длина 25см, ширина 3см
            'phone': (15, 7),  # средний смартфон
            'credit_card': (8.6, 5.4),  # стандартная банковская карта
            'hand': (18, 10)   # средняя ладонь
        }
        return reference_sizes.get(reference_type, (15, 7))  # по умолчанию - телефон

    def _auto_detect_reference(self, reference_objects):
        """Автоматически определяет лучший референсный объект"""
        if not reference_objects:
            return (15, 7)  # размер телефона по умолчанию
        
        # Предпочитаем более надежные объекты
        priority_order = ['credit card', 'phone', 'fork', 'spoon', 'knife', 'hand']
        
        for ref_type in priority_order:
            for obj in reference_objects:
                if obj['type'] == ref_type:
                    return self._get_reference_size(ref_type)
        
        # Возвращаем первый попавшийся
        return self._get_reference_size(reference_objects[0]['type'])

    def _calculate_object_area(self, obj):
        """Рассчитывает площадь объекта в нормализованных координатах"""
        if not obj.bounding_poly.normalized_vertices:
            return 0.1
        
        vertices = obj.bounding_poly.normalized_vertices
        width = abs(vertices[1].x - vertices[0].x)
        height = abs(vertices[2].y - vertices[0].y)
        return width * height

    def _estimate_weight_with_reference(self, food_name, area, reference_size):
        """Оценивает вес еды относительно референсного объекта"""
        ref_length, ref_width = reference_size
        reference_area_cm2 = ref_length * ref_width  # площадь референса в см²
        
        # Преобразуем нормализованную площадь в реальную (предполагаем, что фото занимает ~500см²)
        real_area_cm2 = area * 500
        
        # Отношение площади еды к площади референса
        size_ratio = real_area_cm2 / reference_area_cm2
        
        # Базовые плотности для разных типов еды (г/см³)
        density_factors = {
            'бургер': 0.8,
            'картофель фри': 0.3,
            'пицца': 0.6,
            'салат': 0.4,
            'суп': 1.0,
            'рис': 0.9,
            'паста': 0.7,
            'курица': 1.1,
            'рыба': 1.0,
            'мясо': 1.2,
            'овощи': 0.5,
            'фрукты': 0.6,
            'хлеб': 0.4,
            'сыр': 1.0,
            'десерт': 0.8,
            'мороженое': 0.7,
            'напиток': 1.0
        }
        
        # Находим подходящую плотность
        density = 0.8  # по умолчанию
        food_lower = food_name.lower()
        for food_type, factor in density_factors.items():
            if food_type in food_lower:
                density = factor
                break
        
        # Рассчитываем объем (предполагаем глубину пропорционально площади)
        depth_cm = math.sqrt(real_area_cm2) * 0.5  # эмпирическая формула
        volume_cm3 = real_area_cm2 * depth_cm
        
        # Вес = объем × плотность
        estimated_weight = volume_cm3 * density
        
        # Ограничиваем разумными пределами
        return max(30, min(estimated_weight, 2000))

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
            'reference_detected': False,
            'reference_objects': [],
            'estimated_weights': {}
        }
