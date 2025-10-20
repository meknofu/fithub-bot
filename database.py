import psycopg2
from psycopg2.extras import RealDictCursor
import os
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_tables()

    def connect(self):
        try:
            self.conn = psycopg2.connect(Config.DATABASE_URL, sslmode='require')
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection error: {e}")

    def init_tables(self):
        try:
            with self.conn.cursor() as cur:
                # Таблица пользователей
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        user_type VARCHAR(50),
                        height FLOAT,
                        weight FLOAT,
                        daily_calories FLOAT,
                        trainer_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица связей тренер-ученик
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS trainer_trainee (
                        trainer_id BIGINT,
                        trainee_id BIGINT,
                        PRIMARY KEY (trainer_id, trainee_id)
                    )
                ''')
                
                # Таблица приемов пищи
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS meals (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        food_name VARCHAR(255),
                        weight_grams FLOAT,
                        calories FLOAT,
                        protein FLOAT,
                        fat FLOAT,
                        carbs FLOAT,
                        meal_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица продуктов (из USDA)
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS food_items (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE,
                        calories_per_100g FLOAT,
                        protein_per_100g FLOAT,
                        fat_per_100g FLOAT,
                        carbs_per_100g FLOAT
                    )
                ''')
                
                self.conn.commit()
                logger.info("Tables initialized successfully")
        except Exception as e:
            logger.error(f"Table initialization error: {e}")
            self.conn.rollback()

    def add_user(self, user_data):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO users (id, username, first_name, last_name, user_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    user_type = EXCLUDED.user_type
                ''', (user_data['id'], user_data.get('username'), 
                      user_data['first_name'], user_data.get('last_name'), 
                      user_data['user_type']))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            self.conn.rollback()

    def update_user_metrics(self, user_id, height, weight, daily_calories):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    UPDATE users 
                    SET height = %s, weight = %s, daily_calories = %s
                    WHERE id = %s
                ''', (height, weight, daily_calories, user_id))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating user metrics: {e}")
            self.conn.rollback()

    def add_meal(self, user_id, food_name, weight_grams, calories, protein, fat, carbs, meal_type):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO meals (user_id, food_name, weight_grams, calories, protein, fat, carbs, meal_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (user_id, food_name, weight_grams, calories, protein, fat, carbs, meal_type))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding meal: {e}")
            self.conn.rollback()

    def get_daily_intake(self, user_id, date):
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT * FROM meals 
                    WHERE user_id = %s AND DATE(created_at) = %s
                    ORDER BY created_at
                ''', (user_id, date))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting daily intake: {e}")
            return []

    def add_trainer_trainee(self, trainer_id, trainee_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO trainer_trainee (trainer_id, trainee_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                ''', (trainer_id, trainee_id))
                
                cur.execute('''
                    UPDATE users SET trainer_id = %s WHERE id = %s
                ''', (trainer_id, trainee_id))
                
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding trainer-trainee relationship: {e}")
            self.conn.rollback()

    def get_trainees(self, trainer_id):
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT u.* FROM users u
                    JOIN trainer_trainee tt ON u.id = tt.trainee_id
                    WHERE tt.trainer_id = %s
                ''', (trainer_id,))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting trainees: {e}")
            return []

    def search_food(self, food_name):
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT * FROM food_items 
                    WHERE name ILIKE %s
                    LIMIT 10
                ''', (f'%{food_name}%',))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error searching food: {e}")
            return []

    def get_user(self, user_id):
        """Получает данные пользователя"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def add_food_item(self, food_data):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO food_items (name, calories_per_100g, protein_per_100g, fat_per_100g, carbs_per_100g)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                    calories_per_100g = EXCLUDED.calories_per_100g,
                    protein_per_100g = EXCLUDED.protein_per_100g,
                    fat_per_100g = EXCLUDED.fat_per_100g,
                    carbs_per_100g = EXCLUDED.carbs_per_100g
                ''', (food_data['name'], food_data['calories'], 
                      food_data['protein'], food_data['fat'], 
                      food_data['carbs']))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding food item: {e}")
            self.conn.rollback()

# Глобальный экземпляр базы данных
db = Database()
