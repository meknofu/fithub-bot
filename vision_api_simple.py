import logging
import random

logger = logging.getLogger(__name__)

class SimpleVisionAPI:
    def __init__(self):
        logger.info("✅ Упрощенный Vision API инициализирован")
    
    def analyze_image(self, image_content):
        """Упрощенный анализ изображения для тестирования"""
        try:
            # Список распространенных продуктов
            common_foods = [
                'apple', 'banana', 'bread', 'rice', 'pasta', 
                'chicken', 'egg', 'cheese', 'milk', 'salad',
                'potato', 'tomato', 'carrot', 'onion', 'fish',
                'pizza', 'burger', 'soup', 'yogurt', 'orange'
            ]
            
            # Выбираем случайные продукты для демонстрации
            detected_items = []
            for i in range(random.randint(1, 3)):
                food = random.choice(common_foods)
                detected_items.append({
                    'name': food,
                    'confidence': round(random.uniform(0.7, 0.95), 2),
                    'type': 'sample'
                })
            
            return {
                'success': True,
                'detected_items': detected_items,
                'total_detected': len(detected_items),
                'note': 'Это демонстрационные данные. Для реального распознавания настройте Google Vision API.'
            }
        except Exception as e:
            logger.error(f"Ошибка в SimpleVisionAPI: {e}")
            return {
                'success': False,
                'error': str(e),
                'detected_items': [],
                'total_detected': 0
            }

# Глобальный экземпляр
vision_api = SimpleVisionAPI()
