import psycopg2
from psycopg2.extras import RealDictCursor
import os
from config import Config
import logging
import time

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        """Connect to database with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.conn = psycopg2.connect(
                    Config.DATABASE_URL, 
                    sslmode='require',
                    connect_timeout=10
                )
                logger.info("Database connection established")
                return
            except Exception as e:
                retry_count += 1
                logger.error(f"Database connection attempt {retry_count} failed: {e}")
                if retry_count >= max_retries:
                    logger.error("Max database connection retries reached")
                    raise
                time.sleep(2)
    
    def init_tables(self):
        """Initialize database tables"""
        try:
            with self.conn.cursor() as cur:
                # Users table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        user_type VARCHAR(50),
                        height FLOAT,
                        weight FLOAT,
                        age INTEGER,
                        gender VARCHAR(10),
                        activity_level VARCHAR(50),
                        goal VARCHAR(50),
                        daily_calories FLOAT,
                        trainer_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Trainer-trainee relationship table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS trainer_trainee (
                        trainer_id BIGINT,
                        trainee_id BIGINT,
                        PRIMARY KEY (trainer_id, trainee_id)
                    )
                ''')
                
                # Food items table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS food_items (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE,
                        calories FLOAT,
                        protein FLOAT,
                        fat FLOAT,
                        carbs FLOAT,
                        per_grams INTEGER DEFAULT 100
                    )
                ''')
                
                # Meals table (for meal summaries)
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS meals (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        meal_type VARCHAR(50),
                        date DATE,
                        total_calories FLOAT,
                        total_protein FLOAT,
                        total_fat FLOAT,
                        total_carbs FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Meal items table (individual food items in each meal)
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS meal_items (
                        id SERIAL PRIMARY KEY,
                        meal_id INTEGER REFERENCES meals(id),
                        food_item_id INTEGER REFERENCES food_items(id),
                        weight_grams FLOAT,
                        calories FLOAT,
                        protein FLOAT,
                        fat FLOAT,
                        carbs FLOAT
                    )
                ''')
                
                # Drinks table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS drinks (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        drink_name VARCHAR(255),
                        volume_ml FLOAT,
                        calories FLOAT,
                        protein FLOAT,
                        fat FLOAT,
                        carbs FLOAT,
                        date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.conn.commit()
                logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Table initialization error: {e}")
            self.conn.rollback()
    
    def save_user(self, user_data):
        """Save or update user"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO users (id, username, first_name, last_name, user_type)
                    VALUES (%(id)s, %(username)s, %(first_name)s, %(last_name)s, %(user_type)s)
                    ON CONFLICT (id) DO UPDATE SET
                        username = %(username)s,
                        first_name = %(first_name)s,
                        last_name = %(last_name)s,
                        user_type = %(user_type)s
                ''', user_data)
                self.conn.commit()
                logger.info(f"User saved: {user_data['id']}")
                return True
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            self.conn.rollback()
            return False
    
    def update_user_profile(self, user_id, profile_data):
        """Update user profile"""
        try:
            with self.conn.cursor() as cur:
                fields = ', '.join([f"{key} = %({key})s" for key in profile_data.keys()])
                query = f"UPDATE users SET {fields} WHERE id = %(user_id)s"
                profile_data['user_id'] = user_id
                cur.execute(query, profile_data)
                self.conn.commit()
                logger.info(f"Profile updated for user {user_id}: {profile_data}")
                return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            self.conn.rollback()
            return False
    
    def get_user_profile(self, user_id):
        """Get user profile"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                result = cur.fetchone()
                logger.info(f"Profile fetched for user {user_id}: {result}")
                return result
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def save_meal(self, meal_data):
        """Save meal summary"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO meals (user_id, meal_type, date, total_calories, total_protein, total_fat, total_carbs)
                    VALUES (%(user_id)s, %(meal_type)s, %(date)s, %(calories)s, %(protein)s, %(fat)s, %(carbs)s)
                    RETURNING id
                ''', meal_data)
                meal_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Meal saved with ID {meal_id} for user {meal_data['user_id']}")
                return meal_id
        except Exception as e:
            logger.error(f"Error saving meal: {e}")
            logger.error(f"Meal data was: {meal_data}")
            self.conn.rollback()
            return None
    
    def get_daily_intake(self, user_id, date):
        """Get all meals for a specific day"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT * FROM meals 
                    WHERE user_id = %s AND date = %s
                    ORDER BY created_at
                ''', (user_id, date))
                meals = cur.fetchall()
                
                # Also get drinks for the day
                cur.execute('''
                    SELECT * FROM drinks
                    WHERE user_id = %s AND date = %s
                    ORDER BY created_at
                ''', (user_id, date))
                drinks = cur.fetchall()
                
                # Combine meals and drinks
                all_intake = list(meals) + list(drinks)
                
                logger.info(f"Daily intake for user {user_id} on {date}: {len(all_intake)} items")
                return all_intake
        except Exception as e:
            logger.error(f"Error getting daily intake: {e}")
            return []
    
    def get_food_nutrition(self, food_name):
        """Get nutrition data for a food item"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM food_items WHERE LOWER(name) = LOWER(%s)', (food_name,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error getting food nutrition: {e}")
            return None
    
    def save_drink(self, drink_data):
        """Save drink entry"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO drinks (user_id, drink_name, volume_ml, calories, protein, fat, carbs, date)
                    VALUES (%(user_id)s, %(drink_name)s, %(volume_ml)s, %(calories)s, %(protein)s, %(fat)s, %(carbs)s, %(date)s)
                    RETURNING id
                ''', drink_data)
                drink_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Drink saved with ID {drink_id} for user {drink_data['user_id']}")
                return True
        except Exception as e:
            logger.error(f"Error saving drink: {e}")
            logger.error(f"Drink data was: {drink_data}")
            self.conn.rollback()
            return False
    
    def link_trainer_trainee(self, trainer_id, trainee_id):
        """Link trainer with trainee"""
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
                return True
        except Exception as e:
            logger.error(f"Error linking trainer-trainee: {e}")
            self.conn.rollback()
            return False
    
    def get_trainees(self, trainer_id):
        """Get all trainees for a trainer"""
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

# Global database instance
db = Database()
