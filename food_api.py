import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FoodAPI:
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/api/v0"
    
    def search_product(self, product_name: str) -> Optional[Dict]:
        """Поиск продукта в Open Food Facts"""
        try:
            url = f"{self.base_url}/product/{product_name}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 1:  # Продукт найден
                    product = data['product']
                    
                    # Извлекаем питательную ценность
                    nutriments = product.get('nutriments', {})
                    
                    return {
                        'name': product.get('product_name', product_name),
                        'calories': nutriments.get('energy-kcal_100g'),
                        'protein': nutriments.get('proteins_100g'),
                        'fat': nutriments.get('fat_100g'),
                        'carbs': nutriments.get('carbohydrates_100g'),
                        'serving_size': product.get('serving_size'),
                        'brand': product.get('brands', '')
                    }
            
            # Если не нашли, пробуем поиск
            return self.search_by_query(product_name)
            
        except Exception as e:
            logger.error(f"Food API error: {e}")
            return None
    
    def search_by_query(self, query: str) -> Optional[Dict]:
        """Поиск по запросу"""
        try:
            url = f"{self.base_url}/search"
            params = {
                'search_terms': query,
                'json': 1,
                'page_size': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                if products:
                    product = products[0]
                    nutriments = product.get('nutriments', {})
                    
                    return {
                        'name': product.get('product_name', query),
                        'calories': nutriments.get('energy-kcal_100g'),
                        'protein': nutriments.get('proteins_100g'),
                        'fat': nutriments.get('fat_100g'),
                        'carbs': nutriments.get('carbohydrates_100g'),
                        'serving_size': product.get('serving_size'),
                        'brand': product.get('brands', '')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Food search error: {e}")
            return None
    
    def get_food_info(self, food_name: str, quantity: float = 100) -> Dict:
        """Получение информации о продукте с учетом количества"""
        product = self.search_product(food_name)
        
        if not product:
            # Возвращаем примерные значения по умолчанию
            return self.get_default_nutrition(food_name, quantity)
        
        # Пересчитываем на указанное количество
        ratio = quantity / 100
        
        return {
            'name': product['name'],
            'calories': (product['calories'] or 0) * ratio,
            'protein': (product['protein'] or 0) * ratio,
            'fat': (product['fat'] or 0) * ratio,
            'carbs': (product['carbs'] or 0) * ratio,
            'quantity': quantity,
            'source': 'openfoodfacts'
        }
    
    def get_default_nutrition(self, food_name: str, quantity: float) -> Dict:
        """Примерные значения КБЖУ для распространенных продуктов"""
        default_values = {
            'apple': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 14},
            'banana': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 23},
            'bread': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbs': 49},
            'rice': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28},
            'chicken': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0},
            'egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            'milk': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 5},
            'cheese': {'calories': 402, 'protein': 25, 'fat': 33, 'carbs': 1.3},
            'pasta': {'calories': 131, 'protein': 5, 'fat': 1.1, 'carbs': 25},
            'potato': {'calories': 77, 'protein': 2, 'fat': 0.1, 'carbs': 17},
        }
        
        # Ищем совпадение в названии
        food_lower = food_name.lower()
        for key, values in default_values.items():
            if key in food_lower:
                ratio = quantity / 100
                return {
                    'name': food_name,
                    'calories': values['calories'] * ratio,
                    'protein': values['protein'] * ratio,
                    'fat': values['fat'] * ratio,
                    'carbs': values['carbs'] * ratio,
                    'quantity': quantity,
                    'source': 'default'
                }
        
        # Значения по умолчанию для неизвестных продуктов
        ratio = quantity / 100
        return {
            'name': food_name,
            'calories': 100 * ratio,
            'protein': 5 * ratio,
            'fat': 3 * ratio,
            'carbs': 15 * ratio,
            'quantity': quantity,
            'source': 'unknown'
        }

# Глобальный экземпляр Food API
food_api = FoodAPI()
