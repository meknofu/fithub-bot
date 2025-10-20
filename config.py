import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY')
    
    # Рекомендации по КБЖУ (калории на кг веса)
    CALORIES_PER_KG = {
        'weight_loss': 30,
        'maintenance': 35,
        'weight_gain': 40
    }
    
    # Соотношение БЖУ
    MACRO_RATIO = {
        'protein': 0.3,  # 30%
        'fat': 0.25,     # 25%
        'carbs': 0.45    # 45%
    }
