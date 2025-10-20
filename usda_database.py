import requests
import json
import logging
from typing import Dict, Optional
import sqlite3
import os

logger = logging.getLogger(__name__)

class USDADatabase:
    def __init__(self):
        self.db_path = "usda_foods.db"
        self.init_database()
    
    def init_database(self):
        """Инициализация локальной базы USDA"""
        if not os.path.exists(self.db_path):
            self._create_database()
    
    def _create_database(self):
        """Создание базы данных с популярными продуктами"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                calories REAL,
                protein REAL,
                fat REAL,
                carbs REAL,
                serving_size_g REAL
            )
        ''')
        
        # Добавляем популярные продукты (сокращенная версия USDA)
        popular_foods = [
            # Фрукты
            ('Apple', 'Fruit', 52, 0.3, 0.2, 14, 100),
            ('Banana', 'Fruit', 89, 1.1, 0.3, 23, 100),
            ('Orange', 'Fruit', 47, 0.9, 0.1, 12, 100),
            
            # Овощи
            ('Potato', 'Vegetable', 77, 2.0, 0.1, 17, 100),
            ('Tomato', 'Vegetable', 18, 0.9, 0.2, 4, 100),
            ('Carrot', 'Vegetable', 41, 0.9, 0.2, 10, 100),
            ('Broccoli', 'Vegetable', 34, 2.8, 0.4, 7, 100),
            
            # Мясо и птица
            ('Chicken Breast', 'Meat', 165, 31.0, 3.6, 0, 100),
            ('Beef Steak', 'Meat', 271, 26.0, 18.0, 0, 100),
            ('Salmon', 'Fish', 208, 20.0, 13.0, 0, 100),
            
            # Молочные продукты
            ('Milk', 'Dairy', 42, 3.4, 1.0, 5, 100),
            ('Cheese', 'Dairy', 402, 25.0, 33.0, 1.3, 100),
            ('Yogurt', 'Dairy', 61, 3.5, 3.3, 4.7, 100),
            
            # Крупы и злаки
            ('Rice', 'Grain', 130, 2.7, 0.3, 28, 100),
            ('Pasta', 'Grain', 131, 5.0, 1.1, 25, 100),
            ('Bread', 'Grain', 265, 9.0, 3.2, 49, 100),
            ('Oatmeal', 'Grain', 68, 2.4, 1.4, 12, 100),
            
            # Бобовые
            ('Lentils', 'Legume', 116, 9.0, 0.4, 20, 100),
            ('Chickpeas', 'Legume', 139, 7.0, 2.0, 22, 100),
            
            # Орехи и семена
            ('Almonds', 'Nuts', 579, 21.0, 50.0, 22, 100),
            ('Peanuts', 'Nuts', 567, 26.0, 49.0, 16, 100),
        ]
        
        cursor.executemany('''
            INSERT INTO foods (name, category, calories, protein, fat, carbs, serving_size_g)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', popular_foods)
        
        conn.commit()
        conn.close()
        logger.info("✅ База USDA создана с 20+ популярными продуктами")
    
    def search_food(self, food_name: str) -> Optional[Dict]:
        """Поиск продукта в базе USDA"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ищем точное совпадение
            cursor.execute('''
                SELECT name, category, calories, protein, fat, carbs, serving_size_g
                FROM foods WHERE LOWER(name) = LOWER(?)
            ''', (food_name,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'name': result[0],
                    'category': result[1],
                    'calories': result[2],
                    'protein': result[3],
                    'fat': result[4],
                    'carbs': result[5],
                    'serving_size_g': result[6]
                }
            
            # Ищем частичное совпадение
            cursor.execute('''
                SELECT name, category, calories, protein, fat, carbs, serving_size_g
                FROM foods WHERE LOWER(name) LIKE LOWER(?)
            ''', (f'%{food_name}%',))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'name': result[0],
                    'category': result[1],
                    'calories': result[2],
                    'protein': result[3],
                    'fat': result[4],
                    'carbs': result[5],
                    'serving_size_g': result[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка поиска продукта {food_name}: {e}")
            return None
    
    def calculate_nutrition(self, food_name: str, weight_grams: float) -> Dict:
        """Расчет КБЖУ для указанного веса"""
        food_data = self.search_food(food_name)
        
        if not food_data:
            # Возвращаем примерные значения
            return self._get_estimated_nutrition(food_name, weight_grams)
        
        # Пересчитываем на указанный вес
        ratio = weight_grams / food_data['serving_size_g']
        
        return {
            'name': food_data['name'],
            'calories': food_data['calories'] * ratio,
            'protein': food_data['protein'] * ratio,
            'fat': food_data['fat'] * ratio,
            'carbs': food_data['carbs'] * ratio,
            'weight_grams': weight_grams,
            'source': 'usda'
        }
    
    def _get_estimated_nutrition(self, food_name: str, weight_grams: float) -> Dict:
        """Примерные значения для неизвестных продуктов"""
        estimated_db = {
            'apple': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 14},
            'banana': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 23},
            'rice': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28},
            'chicken': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0},
            'fish': {'calories': 206, 'protein': 22, 'fat': 12, 'carbs': 0},
            'egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1},
            'milk': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 5},
            'bread': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbs': 49},
        }
        
        food_lower = food_name.lower()
        for key, values in estimated_db.items():
            if key in food_lower:
                ratio = weight_grams / 100
                return {
                    'name': food_name,
                    'calories': values['calories'] * ratio,
                    'protein': values['protein'] * ratio,
                    'fat': values['fat'] * ratio,
                    'carbs': values['carbs'] * ratio,
                    'weight_grams': weight_grams,
                    'source': 'estimated'
                }
        
        # Значения по умолчанию
        ratio = weight_grams / 100
        return {
            'name': food_name,
            'calories': 150 * ratio,
            'protein': 10 * ratio,
            'fat': 5 * ratio,
            'carbs': 20 * ratio,
            'weight_grams': weight_grams,
            'source': 'default'
        }

# Глобальный экземпляр
usda_db = USDADatabase()
