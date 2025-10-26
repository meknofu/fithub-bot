
import logging

logger = logging.getLogger(__name__)

class DrinkManager:
    def __init__(self):
        self.drink_database = self._initialize_drink_database()
    
    def _initialize_drink_database(self):
        """Улучшенная база данных популярных напитков"""
        return {
            # Вода и низкокалорийные напитки
            'вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'минеральная вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'газированная вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'содовая': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            
            # Соки
            'апельсиновый сок': {'calories': 45, 'protein': 0.7, 'fat': 0.2, 'carbs': 10.4},
            'яблочный сок': {'calories': 46, 'protein': 0.1, 'fat': 0.1, 'carbs': 11.7},
            'томатный сок': {'calories': 17, 'protein': 0.9, 'fat': 0.1, 'carbs': 3.6},
            'мультифруктовый сок': {'calories': 48, 'protein': 0.4, 'fat': 0.1, 'carbs': 11.6},
            'виноградный сок': {'calories': 60, 'protein': 0.3, 'fat': 0.1, 'carbs': 14.8},
            
            # Газированные напитки
            'кола': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'пепси': {'calories': 41, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'спрайт': {'calories': 40, 'protein': 0, 'fat': 0, 'carbs': 9.9},
            'фанта': {'calories': 46, 'protein': 0, 'fat': 0, 'carbs': 11.4},
            'лимонад': {'calories': 40, 'protein': 0, 'fat': 0, 'carbs': 10},
            
            # Энергетические напитки
            'ред булл': {'calories': 45, 'protein': 0, 'fat': 0, 'carbs': 11},
            'берн': {'calories': 47, 'protein': 0, 'fat': 0, 'carbs': 11.5},
            'адреналин раш': {'calories': 43, 'protein': 0, 'fat': 0, 'carbs': 10.5},
            'монстр': {'calories': 48, 'protein': 0, 'fat': 0, 'carbs': 12},
            
            # Чай и кофе
            'черный чай': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0},
            'зеленый чай': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0},
            'травяной чай': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'кофе черный': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'кофе с сахаром': {'calories': 25, 'protein': 0.3, 'fat': 0, 'carbs': 5},
            'кофе с молоком': {'calories': 15, 'protein': 1, 'fat': 0.5, 'carbs': 2},
            'капучино': {'calories': 45, 'protein': 2, 'fat': 2, 'carbs': 4},
            'латте': {'calories': 60, 'protein': 3, 'fat': 2.5, 'carbs': 5},
            'американо': {'calories': 5, 'protein': 0.2, 'fat': 0, 'carbs': 1},
            'эспрессо': {'calories': 3, 'protein': 0.1, 'fat': 0, 'carbs': 0.5},
            
            # Молочные напитки
            'молоко': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'кефир': {'calories': 41, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'йогурт питьевой': {'calories': 70, 'protein': 3, 'fat': 1.5, 'carbs': 10},
            'ряженка': {'calories': 57, 'protein': 3, 'fat': 2.5, 'carbs': 4.2},
            'простокваша': {'calories': 45, 'protein': 3, 'fat': 1.5, 'carbs': 4},
            'молочный коктейль': {'calories': 120, 'protein': 3, 'fat': 3, 'carbs': 20},
            
            # Спортивные напитки
            'изотоник': {'calories': 24, 'protein': 0, 'fat': 0, 'carbs': 6},
            'протеиновый коктейль': {'calories': 120, 'protein': 20, 'fat': 2, 'carbs': 5},
            'всм': {'calories': 80, 'protein': 15, 'fat': 1, 'carbs': 3},
            
            # Алкоголь (на 100мл)
            'пиво': {'calories': 43, 'protein': 0.5, 'fat': 0, 'carbs': 3.6},
            'вино белое': {'calories': 82, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'вино красное': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'шампанское': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 1.5},
            'водка': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            'виски': {'calories': 250, 'protein': 0, 'fat': 0, 'carbs': 0.1},
            'ром': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            'джин': {'calories': 263, 'protein': 0, 'fat': 0, 'carbs': 0},
        }
    
    def get_drink_kbju(self, drink_name, volume_ml):
        """Рассчитывает КБЖУ для напитка с улучшенным поиском"""
        drink_lower = drink_name.lower().strip()
        
        # Сначала ищем точное совпадение
        if drink_lower in self.drink_database:
            nutrients = self.drink_database[drink_lower]
            ratio = volume_ml / 100
            return {
                'calories': round(nutrients['calories'] * ratio),
                'protein': round(nutrients['protein'] * ratio, 1),
                'fat': round(nutrients['fat'] * ratio, 1),
                'carbs': round(nutrients['carbs'] * ratio, 1)
            }
        
        # Затем ищем частичное совпадение
        for drink, nutrients in self.drink_database.items():
            if drink in drink_lower:
                ratio = volume_ml / 100
                return {
                    'calories': round(nutrients['calories'] * ratio),
                    'protein': round(nutrients['protein'] * ratio, 1),
                    'fat': round(nutrients['fat'] * ratio, 1),
                    'carbs': round(nutrients['carbs'] * ratio, 1)
                }
        
        # Если не нашли, используем умные предположения на основе названия
        return self._estimate_kbju_by_name(drink_lower, volume_ml)
    
    def _estimate_kbju_by_name(self, drink_name, volume_ml):
        """Умная оценка КБЖУ на основе названия напитка"""
        ratio = volume_ml / 100
        
        # Категории напитков и их средние значения
        if any(word in drink_name for word in ['вода', 'минеральная', 'газированная', 'содовая']):
            return {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        
        elif any(word in drink_name for word in ['сок', 'juice', 'нектар']):
            return {
                'calories': round(45 * ratio),
                'protein': round(0.5 * ratio, 1),
                'fat': round(0.1 * ratio, 1),
                'carbs': round(11 * ratio, 1)
            }
        
        elif any(word in drink_name for word in ['кола', 'пепси', 'спрайт', 'фанта', 'лимонад', 'газировка']):
            return {
                'calories': round(42 * ratio),
                'protein': 0,
                'fat': 0,
                'carbs': round(10.5 * ratio, 1)
            }
        
        elif any(word in drink_name for word in ['чай', 'кофе']):
            if 'сахар' in drink_name or 'сахаром' in drink_name:
                return {
                    'calories': round(25 * ratio),
                    'protein': round(0.3 * ratio, 1),
                    'fat': 0,
                    'carbs': round(5 * ratio, 1)
                }
            elif 'молок' in drink_name or 'молоч' in drink_name:
                return {
                    'calories': round(15 * ratio),
                    'protein': round(1 * ratio, 1),
                    'fat': round(0.5 * ratio, 1),
                    'carbs': round(2 * ratio, 1)
                }
            else:
                return {
                    'calories': round(2 * ratio),
                    'protein': round(0.2 * ratio, 1),
                    'fat': 0,
                    'carbs': round(0.5 * ratio, 1)
                }
        
        elif any(word in drink_name for word in ['молок', 'кефир', 'ряженка', 'йогурт']):
            return {
                'calories': round(50 * ratio),
                'protein': round(3 * ratio, 1),
                'fat': round(1.5 * ratio, 1),
                'carbs': round(5 * ratio, 1)
            }
        
        elif any(word in drink_name for word in ['энергетик', 'ред булл', 'берн', 'монстр']):
            return {
                'calories': round(45 * ratio),
                'protein': 0,
                'fat': 0,
                'carbs': round(11 * ratio, 1)
            }
        
        elif any(word in drink_name for word in ['пиво', 'вино', 'шампанское', 'водка', 'виски']):
            return {
                'calories': round(80 * ratio),
                'protein': round(0.2 * ratio, 1),
                'fat': 0,
                'carbs': round(2 * ratio, 1)
            }
        
        # По умолчанию - низкокалорийный напиток
        else:
            return {
                'calories': round(20 * ratio),
                'protein': round(0.1 * ratio, 1),
                'fat': 0,
                'carbs': round(5 * ratio, 1)
            }
