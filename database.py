import sqlite3
import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="fithub.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Пользователи
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    role TEXT CHECK(role IN ('trainer', 'trainee')),
                    height REAL,
                    weight REAL,
                    age INTEGER,
                    gender TEXT CHECK(gender IN ('male', 'female')),
                    goal TEXT CHECK(goal IN ('lose', 'gain', 'maintain')),
                    activity_level REAL DEFAULT 1.375,
                    daily_calories REAL,
                    protein_goal REAL,
                    fat_goal REAL,
                    carb_goal REAL,
                    trainer_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trainer_id) REFERENCES users (user_id)
                )
            ''')
            
            # Дневник питания
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS food_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT DEFAULT CURRENT_DATE,
                    food_name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    calories REAL,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
                    meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
                    confirmed BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Связи тренер-ученик
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trainer_relationships (
                    trainer_id INTEGER,
                    trainee_id INTEGER UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (trainer_id, trainee_id),
                    FOREIGN KEY (trainer_id) REFERENCES users (user_id),
                    FOREIGN KEY (trainee_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def add_user(self, user_data):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, role, height, weight, age, gender, 
                 goal, activity_level, daily_calories, protein_goal, fat_goal, carb_goal, trainer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', user_data)
    
    def get_user(self, user_id):
        with self.get_connection() as conn:
            return conn.execute(
                'SELECT * FROM users WHERE user_id = ?', (user_id,)
            ).fetchone()
    
    def add_food_entry(self, user_id, food_name, quantity, calories, protein, fat, carbs, meal_type, confirmed=True):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO food_log 
                (user_id, food_name, quantity, calories, protein, fat, carbs, meal_type, confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, food_name, quantity, calories, protein, fat, carbs, meal_type, confirmed))
    
    def get_daily_summary(self, user_id, date=None):
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            result = conn.execute('''
                SELECT 
                    SUM(calories), 
                    SUM(protein), 
                    SUM(fat), 
                    SUM(carbs)
                FROM food_log 
                WHERE user_id = ? AND date = ? AND confirmed = 1
            ''', (user_id, date)).fetchone()
            
            return result or (0, 0, 0, 0)
    
    def link_trainer_trainee(self, trainer_id, trainee_id):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE users SET trainer_id = ? WHERE user_id = ?',
                (trainer_id, trainee_id)
            )
            conn.execute('''
                INSERT OR REPLACE INTO trainer_relationships 
                (trainer_id, trainee_id) VALUES (?, ?)
            ''', (trainer_id, trainee_id))
    
    def get_trainees(self, trainer_id):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT u.user_id, u.username, u.first_name 
                FROM users u
                JOIN trainer_relationships tr ON u.user_id = tr.trainee_id
                WHERE tr.trainer_id = ?
            ''', (trainer_id,)).fetchall()
    
    def get_todays_entries(self, user_id):
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT id, food_name, quantity, calories, protein, fat, carbs, meal_type
                FROM food_log 
                WHERE user_id = ? AND date = ? AND confirmed = 1
                ORDER BY created_at
            ''', (user_id, today)).fetchall()

# Глобальный экземпляр базы данных
db = Database()
