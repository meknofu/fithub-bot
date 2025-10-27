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
        """Основная функция распознавания еды"""
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
            
            logger.info(f"Found {len(objects)} objects and {len(labels)} labels")
            
            all_items = []
            
            # Собираем все продукты из objects
            for obj in objects:
                if self._is_food_item(obj.name) and obj.score > 0.5:
                    area = self._calculate_object_area(obj)
                    logger.info(f"Food object: {obj.name} (score: {obj.score}, area: {area})")
                    
                    all_items.append({
                        'name': obj.name,
                        'confidence': obj.score,
                        'type': 'object',
                        'score': obj.score + 0.2,
                        'area': area
                    })
            
            # Собираем все продукты из labels
            for label in labels:
                if self._is_food_item(label.description) and label.score > 0.6:
                    logger.info(f"Food label: {label.description} (score: {label.score})")
                    
                    all_items.append({
                        'name': label.description,
                        'confidence': label.score,
                        'type': 'label', 
                        'score': label.score,
                        'area': 0.15  # средняя площадь для labels
                    })
            
            # Умная группировка для бургеров и фастфуда
            food_items = self._smart_burger_grouping(all_items)
            
            logger.info(f"After grouping: {len(food_items)} food items")
            
            if not food_items:
                return self._get_fallback_response()
            
            detected_text = texts[0].description if texts else ""
            
            # Оцениваем вес
            estimated_weights = self.estimate_weights(food_items)
            logger.info(f"Estimated weights: {estimated_weights}")
            
            return {
                'food_items': food_items,
                'detected_text': detected_text,
                'estimated_weights': estimated_weights
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()

    def estimate_weights(self, food_items):
        """Упрощенная и надежная оценка веса"""
        estimated_weights = {}
        
        for item in food_items:
            name = item['name'].lower()
            area = item.get('area', 0.1)
            
            logger.info(f"Estimating weight for: {name} (area: {area})")
            
            # Базовые веса для разных типов еды
            weight_rules = [
                # Напитки
                (['напиток', 'drink', 'кофе', 'чай', 'сок', 'cola', 'пепси'], 330),
                (['вода', 'water', 'минеральная'], 500),
                
                # Фастфуд
                (['бургер', 'burger', 'гамбургер', 'чизбургер'], 250),
                (['картофель фри', 'fries', 'фри'], 150),
                (['пицца', 'pizza'], 300),
                (['сэндвич', 'sandwich', 'бургер'], 200),
                (['фастфуд', 'fast food'], 350),
                
                # Основные блюда
                (['курица', 'chicken', 'цыпленок'], 180),
                (['рыба', 'fish', 'лосось', 'тунец'], 200),
                (['мясо', 'meat', 'говядина', 'свинина'], 220),
                (['стейк', 'steak'], 250),
                
                # Гарниры
                (['рис', 'rice'], 150),
                (['паста', 'pasta', 'макароны', 'спагетти'], 200),
                (['картофель', 'potato'], 180),
                (['гречка', 'гречневая'], 150),
                (['пюре', 'пюре картофельное'], 200),
                
                # Салаты и овощи
                (['салат', 'salad'], 150),
                (['овощ', 'vegetable', 'огур', 'помидор', 'морков'], 120),
                (['суп', 'soup', 'борщ'], 300),
                
                # Завтраки
                (['яичница', 'омлет', 'eggs', 'яйцо'], 120),
                (['каша', 'овсянка', ' oatmeal'], 200),
                (['блины', 'pancake', 'блин'], 150),
                
                # Десерты
                (['десерт', 'dessert', 'торт', 'cake', 'пирог'], 150),
                (['мороженое', 'ice cream'], 100),
                (['йогурт', 'yogurt'], 150),
                
                # Хлеб и выпечка
                (['хлеб', 'bread', 'булка'], 100),
                (['сыр', 'cheese'], 80),
            ]
            
            # Ищем подходящее правило
            base_weight = 200  # значение по умолчанию
            for keywords, weight in weight_rules:
                if any(keyword in name for keyword in keywords):
                    base_weight = weight
                    logger.info(f"Found match: {keywords} -> {weight}g")
                    break
            
            # Корректируем вес на основе размера
            size_multiplier = self._calculate_size_multiplier(area)
            estimated_weight = base_weight * size_multiplier
            
            # Ограничиваем разумными пределами
            estimated_weight = max(50, min(estimated_weight, 1000))
            
            estimated_weights[name] = int(estimated_weight)
            logger.info(f"Final weight for {name}: {estimated_weights[name]}g (base: {base_weight}, multiplier: {size_multiplier})")
        
        return estimated_weights

    def _calculate_size_multiplier(self, area):
        """Рассчитывает множитель размера на основе площади"""
        logger.info(f"Calculating size multiplier for area: {area}")
        
        if area < 0.03:
            multiplier = 0.5   # Очень маленький
        elif area < 0.07:
            multiplier = 0.7   # Маленький
        elif area < 0.15:
            multiplier = 1.0   # Средний
        elif area < 0.25:
            multiplier = 1.4   # Большой
        else:
            multiplier = 1.8   # Очень большой
            
        logger.info(f"Size multiplier: {multiplier}")
        return multiplier

    def _calculate_object_area(self, obj):
        """Рассчитывает площадь объекта"""
        if not obj.bounding_poly.normalized_vertices:
            return 0.1
        
        vertices = obj.bounding_poly.normalized_vertices
        width = abs(vertices[1].x - vertices[0].x)
        height = abs(vertices[2].y - vertices[0].y)
        area = width * height
        
        logger.info(f"Object area calculation: {obj.name} -> width: {width:.3f}, height: {height:.3f}, area: {area:.3f}")
        return area

    def _smart_burger_grouping(self, items):
        """Умная группировка для бургеров и фастфуда"""
        if not items:
            return []
        
        items.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Items before grouping: {[item['name'] for item in items]}")
        
        # Определяем, есть ли бургер на фото
        has_burger = any('бургер' in item['name'].lower() or 'burger' in item['name'].lower() for item in items)
        has_burger_components = any(comp in item['name'].lower() for item in items for comp in ['bun', 'bread', 'булка', 'котлета', 'patty'])
        
        logger.info(f"Has burger: {has_burger}, has components: {has_burger_components}")
        
        # Если есть бургер или его компоненты, применяем специальную логику
        if has_burger or has_burger_components:
            result = self._group_burger_items(items)
        else:
            result = self._remove_duplicates_and_general(items)
        
        logger.info(f"Items after grouping: {[item['name'] for item in result]}")
        return result

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
        
        # Находим самый уверенный бургер
        burger_items = [item for item in items if any(kw in item['name'].lower() for kw in burger_keywords)]
        component_items = [item for item in items if any(kw in item['name'].lower() for kw in burger_component_keywords)]
        
        final_items = []
        
        # Добавляем бургер (если нашли)
        if burger_items:
            best_burger = max(burger_items, key=lambda x: x['score'])
            # Объединяем площадь компонентов для более точной оценки
            total_area = best_burger.get('area', 0.15)
            if component_items:
                total_area += sum(item.get('area', 0.05) for item in component_items[:3]) * 0.3
            
            final_items.append({
                'name': 'бургер',
                'confidence': best_burger['confidence'],
                'type': 'burger',
                'score': best_burger['score'],
                'area': min(total_area, 0.4)  # ограничиваем максимальную площадь
            })
        # Или создаем бургер из компонентов
        elif component_items:
            best_component = max(component_items, key=lambda x: x['score'])
            total_area = best_component.get('area', 0.15) * 1.5
            
            final_items.append({
                'name': 'бургер',
                'confidence': best_component['confidence'],
                'type': 'burger_inferred',
                'score': best_component['score'],
                'area': total_area
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
        
        return final_items[:3]

    def _remove_duplicates_and_general(self, items):
        """Убирает дубликаты и общие категории"""
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
            'breakfast', 'завтрак', 'lunch', 'обед', 'dinner', 'ужин',
            'potato', 'картофель', 'tomato', 'помидор', 'cucumber', 'огурец'
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
            'estimated_weights': {}
        }
