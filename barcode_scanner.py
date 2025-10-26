import logging
import requests
import json

logger = logging.getLogger(__name__)

class BarcodeScanner:
    def __init__(self):
        self.open_food_facts_url = "https://world.openfoodfacts.org/api/v0/product/"
        
    async def scan_barcode(self, barcode):
        """Сканирует штрих-код через Open Food Facts API"""
        try:
            response = requests.get(f"{self.open_food_facts_url}{barcode}.json")
            data = response.json()
            
            if data.get('status') == 1:  # Продукт найден
                product = data['product']
                
                # Извлекаем информацию о продукте
                product_name = product.get('product_name', 'Неизвестный продукт')
                brands = product.get('brands', '')
                
                # Извлекаем nutritional information
                nutriments = product.get('nutriments', {})
                
                kbju = {
                    'name': f"{brands} {product_name}" if brands else product_name,
                    'calories': round(nutriments.get('energy-kcal_100g', 0)),
                    'protein': round(nutriments.get('proteins_100g', 0), 1),
                    'fat': round(nutriments.get('fat_100g', 0), 1),
                    'carbs': round(nutriments.get('carbohydrates_100g', 0), 1)
                }
                
                return kbju
            else:
                return None
                
        except Exception as e:
            logger.error(f"Barcode scan error: {e}")
            return None

class DrinkManager:
    def __init__(self):
        self.barcode_scanner = BarcodeScanner()
        self.drink_database = self._initialize_drink_database()
    
    def _initialize_drink_database(self):
        """База данных популярных напитков"""
        return {
            # Вода и низкокалорийные напитки
            'вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'минеральная вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'газированная вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            
            # Соки
            'апельсиновый сок': {'calories': 45, 'protein': 0.7, 'fat': 0.2, 'carbs': 10.4},
            'яблочный сок': {'calories': 46, 'protein': 0.1, 'fat': 0.1, 'carbs': 11.7},
            'томатный сок': {'calories': 17, 'protein': 0.9, 'fat': 0.1, 'carbs': 3.6},
            'мультифруктовый сок': {'calories': 48, 'protein': 0.4, 'fat': 0.1, 'carbs': 11.6},
            
            # Газированные напитки
            'кола': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'пепси': {'calories': 41, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'спрайт': {'calories': 40, 'protein': 0, 'fat': 0, 'carbs': 9.9},
            'фанта': {'calories': 46, 'protein': 0, 'fat': 0, 'carbs': 11.4},
            
            # Энергетические напитки
            'ред булл': {'calories': 45, 'protein': 0, 'fat': 0, 'carbs': 11},
            'берн': {'calories': 47, 'protein': 0, 'fat': 0, 'carbs': 11.5},
            'адреналин раш': {'calories': 43, 'protein': 0, 'fat': 0, 'carbs': 10.5},
            
            # Чай и кофе
            'черный чай': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0},
            'зеленый чай': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0},
            'кофе черный': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'кофе с сахаром': {'calories': 25, 'protein': 0.3, 'fat': 0, 'carbs': 5},
            'кофе с молоком': {'calories': 15, 'protein': 1, 'fat': 0.5, 'carbs': 2},
            'капучино': {'calories': 45, 'protein': 2, 'fat': 2, 'carbs': 4},
            'латте': {'calories': 60, 'protein': 3, 'fat': 2.5, 'carbs': 5},
            
            # Молочные напитки
            'молоко': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'кефир': {'calories': 41, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'йогурт питьевой': {'calories': 70, 'protein': 3, 'fat': 1.5, 'carbs': 10},
            'ряженка': {'calories': 57, 'protein': 3, 'fat': 2.5, 'carbs': 4.2},
            
            # Спортивные напитки
            'изотоник': {'calories': 24, 'protein': 0, 'fat': 0, 'carbs': 6},
            'протеиновый коктейль': {'calories': 120, 'protein': 20, 'fat': 2, 'carbs': 5},
            
            # Алкоголь (на 100мл)
            'пиво': {'calories': 43, 'protein': 0.5, 'fat': 0, 'carbs': 3.6},
            'вино белое': {'calories': 82, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'вино красное': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'шампанское': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 1.5},
        }
    
    def get_drink_kbju(self, drink_name, volume_ml):
        """Рассчитывает КБЖУ для напитка"""
        drink_lower = drink_name.lower()
        
        # Ищем в базе данных
        for drink, nutrients in self.drink_database.items():
            if drink in drink_lower:
                ratio = volume_ml / 100  # База на 100мл
                return {
                    'calories': round(nutrients['calories'] * ratio),
                    'protein': round(nutrients['protein'] * ratio, 1),
                    'fat': round(nutrients['fat'] * ratio, 1),
                    'carbs': round(nutrients['carbs'] * ratio, 1)
                }
        
        # Если не нашли, используем средние значения
        return {
            'calories': round(30 * volume_ml / 100),  # Средние 30 ккал на 100мл
            'protein': 0,
            'fat': 0,
            'carbs': round(7 * volume_ml / 100, 1)
        }
    
    async def handle_barcode_photo(self, photo_bytes):
        """Обрабатывает фото штрих-кода"""
        # В реальной реализации здесь будет интеграция с библиотекой для распознавания штрих-кодов
        # Например: pyzbar, OpenCV
        # Пока возвращаем заглушку
        return None
