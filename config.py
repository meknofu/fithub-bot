import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY')
    
    # CPFC recommendations (calories per kg of body weight)
    CALORIES_PER_KG = {
        'weight_loss': 30,
        'maintenance': 35,
        'weight_gain': 40
    }
    
    # Macronutrient ratio
    MACRO_RATIO = {
        'protein': 0.3,   # 30%
        'fat': 0.25,      # 25%
        'carbs': 0.45     # 45%
    }
