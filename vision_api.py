from google.cloud import vision
import io
import logging
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

    # Остальные методы остаются без изменений...
    def _smart_burger_grouping(self, items):
        # ... (предыдущая реализация)
        pass
    
    def _is_food_item(self, item_name):
        # ... (предыдущая реализация)
        pass

    def _get_fallback_response(self):
        return {
            'food_items': [],
            'reference_detected': False,
            'reference_objects': [],
            'estimated_weights': {}
        }
