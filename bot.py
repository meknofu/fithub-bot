import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from config import Config
from database import db
from vision_api import VisionAPI
from cpfc_calculator import CPFCCalculator
from user_manager import UserManager
from drink_manager import DrinkManager
from keyboards import *
import io
from datetime import datetime

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class FithubBot:
    def __init__(self):
        self.db = db
        self.vision = VisionAPI()
        self.calculator = CPFCCalculator()
        self.user_manager = UserManager()
        self.drink_manager = DrinkManager()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        await update.message.reply_html(
            f"Welcome to FITHUB!\n\n"
            f"Hi, {user.first_name}! I'm your personal nutrition assistant.\n\n"
            f"I will help you:\n"
            f"• Track your daily nutrition\n"
            f"• Calculate calories and macros\n"
            f"• Recognize food from photos\n"
            f"• Monitor your progress\n\n"
            f"Who are you?",
            reply_markup=get_user_type_keyboard()
        )
        
        self.user_manager.set_user_state(user.id, 'awaiting_user_type')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        state = self.user_manager.get_user_state(user_id)
        
        logger.info(f"User {user_id} in state {state} sent: {text}")
        
        # User type selection
        if state == 'awaiting_user_type':
            if 'Trainer' in text:
                user_data = {'user_type': 'trainer'}
                self.db.save_user({
                    'id': user_id,
                    'username': update.effective_user.username,
                    'first_name': update.effective_user.first_name,
                    'last_name': update.effective_user.last_name,
                    'user_type': 'trainer'
                })
                await update.message.reply_text(
                    "You are registered as a Trainer!\n\n"
                    "Now you can add your trainees and monitor their nutrition.\n\n"
                    "Commands:\n"
                    "/add_trainee - Add trainee\n"
                    "/my_trainees - View my trainees\n"
                    "/stats - Trainee statistics",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'main_menu')
                
            elif 'Trainee' in text:
                self.db.save_user({
                    'id': user_id,
                    'username': update.effective_user.username,
                    'first_name': update.effective_user.first_name,
                    'last_name': update.effective_user.last_name,
                    'user_type': 'trainee'
                })
                await update.message.reply_text(
                    "You are registered as a Trainee!\n\n"
                    "Let's set up your profile to calculate your personalized nutrition plan.\n\n"
                    "Please enter your height in cm (e.g., 175):",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'awaiting_height')
        
        # Height input
        elif state == 'awaiting_height':
            try:
                height = float(text)
                if height < 100 or height > 250:
                    await update.message.reply_text("Please enter a valid height (100-250 cm):")
                    return
                
                self.user_manager.set_user_state(user_id, 'awaiting_weight', {'height': height})
                await update.message.reply_text(f"Height: {height} cm\n\nNow enter your weight in kg (e.g., 70):")
            except ValueError:
                await update.message.reply_text("Please enter a valid number:")
        
        # Weight input
        elif state == 'awaiting_weight':
            try:
                weight = float(text)
                if weight < 30 or weight > 300:
                    await update.message.reply_text("Please enter a valid weight (30-300 kg):")
                    return
                
                data = self.user_manager.get_user_data(user_id)
                data['weight'] = weight
                self.user_manager.set_user_state(user_id, 'awaiting_age', data)
                await update.message.reply_text(f"Weight: {weight} kg\n\nNow enter your age (e.g., 25):")
            except ValueError:
                await update.message.reply_text("Please enter a valid number:")
        
        # Age input
        elif state == 'awaiting_age':
            try:
                age = int(text)
                if age < 10 or age > 100:
                    await update.message.reply_text("Please enter a valid age (10-100):")
                    return
                
                data = self.user_manager.get_user_data(user_id)
                data['age'] = age
                self.user_manager.set_user_state(user_id, 'awaiting_gender', data)
                await update.message.reply_text(
                    f"Age: {age}\n\nSelect your gender:",
                    reply_markup=ReplyKeyboardMarkup([['Male', 'Female']], one_time_keyboard=True, resize_keyboard=True)
                )
            except ValueError:
                await update.message.reply_text("Please enter a valid number:")
        
        # Gender selection
        elif state == 'awaiting_gender':
            if text in ['Male', 'Female']:
                data = self.user_manager.get_user_data(user_id)
                data['gender'] = text.lower()
                self.user_manager.set_user_state(user_id, 'awaiting_activity_level', data)
                await update.message.reply_text(
                    f"Gender: {text}\n\nSelect your activity level:",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Sedentary (minimal activity)'],
                        ['Light (exercise 1-3 days/week)'],
                        ['Moderate (exercise 3-5 days/week)'],
                        ['Active (exercise 6-7 days/week)'],
                        ['Very Active (intense exercise + physical job)']
                    ], one_time_keyboard=True, resize_keyboard=True)
                )
            else:
                await update.message.reply_text("Please select Male or Female:")
        
        # Activity level selection
        elif state == 'awaiting_activity_level':
            activity_map = {
                'Sedentary': 'sedentary',
                'Light': 'light',
                'Moderate': 'medium',
                'Active': 'active',
                'Very Active': 'very_active'
            }
            
            activity_level = None
            for key, value in activity_map.items():
                if key in text:
                    activity_level = value
                    break
            
            if activity_level:
                data = self.user_manager.get_user_data(user_id)
                data['activity_level'] = activity_level
                self.user_manager.set_user_state(user_id, 'awaiting_goal', data)
                await update.message.reply_text(
                    f"Activity level set\n\nSelect your goal:",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Weight Loss'],
                        ['Maintenance'],
                        ['Weight Gain']
                    ], one_time_keyboard=True, resize_keyboard=True)
                )
            else:
                await update.message.reply_text("Please select an activity level from the menu:")
        
        # Goal selection
        elif state == 'awaiting_goal':
            goal_map = {
                'Weight Loss': 'weight_loss',
                'Maintenance': 'maintenance',
                'Weight Gain': 'weight_gain'
            }
            
            goal = goal_map.get(text)
            
            if goal:
                data = self.user_manager.get_user_data(user_id)
                data['goal'] = goal
                
                # Calculate CPFC
                cpfc = self.calculator.calculate_daily_cpfc(
                    weight=data['weight'],
                    height=data['height'],
                    age=data['age'],
                    gender=data['gender'],
                    activity_level=data['activity_level'],
                    goal=goal
                )
                
                # Save profile
                profile_data = {
                    'height': data['height'],
                    'weight': data['weight'],
                    'age': data['age'],
                    'gender': data['gender'],
                    'activity_level': data['activity_level'],
                    'goal': goal,
                    'daily_calories': cpfc['calories']
                }
                self.db.update_user_profile(user_id, profile_data)
                
                await update.message.reply_html(
                    f"<b>Profile completed!</b>\n\n"
                    f"<b>Your personalized nutrition plan:</b>\n\n"
                    f"Calories: <b>{cpfc['calories']:.0f} kcal/day</b>\n"
                    f"Protein: <b>{cpfc['protein']:.0f} g/day</b>\n"
                    f"Fat: <b>{cpfc['fat']:.0f} g/day</b>\n"
                    f"Carbs: <b>{cpfc['carbs']:.0f} g/day</b>\n\n"
                    f"Now you can track your meals!\n\n"
                    f"<b>Commands:</b>\n"
                    f"/add_meal - Add meal\n"
                    f"/add_drink - Add drink\n"
                    f"/today - Today's summary\n"
                    f"/profile - View profile",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'main_menu')
            else:
                await update.message.reply_text("Please select a goal from the menu:")
        
        # Meal type selection
        elif state == 'awaiting_meal_type':
            if text in ['Breakfast', 'Lunch', 'Snack', 'Dinner']:
                data = self.user_manager.get_user_data(user_id)
                data['meal_type'] = text.lower()
                self.user_manager.set_user_state(user_id, 'awaiting_food_photo', data)
                await update.message.reply_text(
                    f"Please send a photo of your {text.lower()}.\n\n"
                    f"Tip: For better recognition, include a reference object (fork, spoon, card) in the photo.",
                    reply_markup=remove_keyboard()
                )
            else:
                await update.message.reply_text(
                    "Please select a meal type:",
                    reply_markup=get_meal_type_keyboard()
                )
        
        # Confirmation of recognized food
        elif state == 'awaiting_confirmation':
            if '✅' in text or 'Yes' in text:
                data = self.user_manager.get_user_data(user_id)
                
                # Save meal
                meal_data = {
                    'user_id': user_id,
                    'meal_type': data['meal_type'],
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'calories': data['total_calories'],
                    'protein': data['total_protein'],
                    'fat': data['total_fat'],
                    'carbs': data['total_carbs']
                }
                
                meal_id = self.db.save_meal(meal_data)
                
                if meal_id:
                    # Get remaining CPFC for the day
                    remaining = self.calculator.get_remaining_cpfc(
                        user_id,
                        datetime.now().strftime('%Y-%m-%d')
                    )
                    
                    if remaining:
                        await update.message.reply_html(
                            f"<b>Meal saved!</b>\n\n"
                            f"<b>Remaining for today:</b>\n\n"
                            f"Calories: <b>{remaining['remaining_calories']:.0f} kcal</b>\n"
                            f"Protein: <b>{remaining['remaining_protein']:.0f} g</b>\n"
                            f"Fat: <b>{remaining['remaining_fat']:.0f} g</b>\n"
                            f"Carbs: <b>{remaining['remaining_carbs']:.0f} g</b>",
                            reply_markup=remove_keyboard()
                        )
                    else:
                        await update.message.reply_text(
                            "Meal saved successfully!",
                            reply_markup=remove_keyboard()
                        )
                    
                    self.user_manager.set_user_state(user_id, 'main_menu')
                else:
                    await update.message.reply_text(
                        "Error saving meal. Please try again.",
                        reply_markup=remove_keyboard()
                    )
            
            elif '❌' in text or 'No' in text:
                await update.message.reply_text(
                    "Please enter the food items and their weights manually.\n\n"
                    "Format: food name - weight in grams\n"
                    "Example:\n"
                    "Chicken breast - 150\n"
                    "Rice - 100\n"
                    "Salad - 80",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'awaiting_manual_input')
        
        # Manual food input
        elif state == 'awaiting_manual_input':
            data = self.user_manager.get_user_data(user_id)
            
            # Parse input
            lines = text.strip().split('\n')
            food_items = []
            
            for line in lines:
                try:
                    # Format: food name - weight
                    parts = line.split('-')
                    if len(parts) == 2:
                        food_name = parts[0].strip()
                        weight = float(parts[1].strip())
                        food_items.append({'name': food_name, 'weight': weight})
                except:
                    continue
            
            if not food_items:
                await update.message.reply_text(
                    "Could not parse input. Please use the format:\n\n"
                    "food name - weight\n\n"
                    "Example:\n"
                    "Chicken - 150\n"
                    "Rice - 100"
                )
                return
            
            # Calculate CPFC for meal
            meal_cpfc = self.calculator.calculate_meal_cpfc(food_items)
            
            # Display for confirmation
            items_text = "\n".join([f"• {item['name']}: {item['weight']}g" for item in food_items])
            
            data['food_items'] = food_items
            data['total_calories'] = meal_cpfc['calories']
            data['total_protein'] = meal_cpfc['protein']
            data['total_fat'] = meal_cpfc['fat']
            data['total_carbs'] = meal_cpfc['carbs']
            
            self.user_manager.set_user_state(user_id, 'awaiting_confirmation', data)
            
            await update.message.reply_html(
                f"<b>Your meal:</b>\n\n"
                f"{items_text}\n\n"
                f"<b>Nutrition:</b>\n"
                f"Calories: <b>{meal_cpfc['calories']:.0f} kcal</b>\n"
                f"Protein: <b>{meal_cpfc['protein']:.0f} g</b>\n"
                f"Fat: <b>{meal_cpfc['fat']:.0f} g</b>\n"
                f"Carbs: <b>{meal_cpfc['carbs']:.0f} g</b>\n\n"
                f"Is this correct?",
                reply_markup=get_confirm_keyboard()
            )
        
        # Drink name input
        elif state == 'awaiting_drink_name':
            drink_name = text.strip()
            
            # Search in database
            drink_info = self.drink_manager.get_drink_nutrition(drink_name, 250)  # Default 250ml
            
            if drink_info:
                data = {'drink_name': drink_name, 'drink_info': drink_info}
                self.user_manager.set_user_state(user_id, 'awaiting_drink_volume', data)
                await update.message.reply_text(
                    f"Found: {drink_name}\n\n"
                    f"Select volume:",
                    reply_markup=get_drink_volumes_keyboard()
                )
            else:
                # Search for similar drinks
                similar = self.drink_manager.search_drinks(drink_name)
                
                if similar:
                    await update.message.reply_text(
                        f"Drink '{drink_name}' not found.\n\n"
                        f"Did you mean:\n" + "\n".join(f"• {d}" for d in similar[:5]) + "\n\n"
                        f"Please enter the drink name again:",
                        reply_markup=remove_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"Drink '{drink_name}' not found in database.\n\n"
                        f"Please try another name or add manually.\n\n"
                        f"Enter drink name:",
                        reply_markup=remove_keyboard()
                    )
        
        # Drink volume selection
        elif state == 'awaiting_drink_volume':
            volume_ml = None
            
            if 'ml' in text or 'glass' in text or 'can' in text or 'bottle' in text or 'liter' in text:
                # Extract number
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    volume_ml = int(numbers[0])
            elif 'Other' in text:
                await update.message.reply_text(
                    "Enter volume in ml (e.g., 350):",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'awaiting_custom_volume')
                return
            
            if volume_ml:
                data = self.user_manager.get_user_data(user_id)
                drink_name = data['drink_name']
                
                # Recalculate with actual volume
                drink_info = self.drink_manager.get_drink_nutrition(drink_name, volume_ml)
                
                # Save drink
                drink_data = {
                    'user_id': user_id,
                    'drink_name': drink_name,
                    'volume_ml': volume_ml,
                    'calories': drink_info['calories'],
                    'protein': drink_info['protein'],
                    'fat': drink_info['fat'],
                    'carbs': drink_info['carbs'],
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
                if self.db.save_drink(drink_data):
                    await update.message.reply_html(
                        f"<b>Drink saved!</b>\n\n"
                        f"{drink_name} ({volume_ml}ml)\n\n"
                        f"<b>Nutrition:</b>\n"
                        f"Calories: <b>{drink_info['calories']:.0f} kcal</b>\n"
                        f"Protein: <b>{drink_info['protein']:.1f} g</b>\n"
                        f"Fat: <b>{drink_info['fat']:.1f} g</b>\n"
                        f"Carbs: <b>{drink_info['carbs']:.1f} g</b>",
                        reply_markup=remove_keyboard()
                    )
                    self.user_manager.set_user_state(user_id, 'main_menu')
                else:
                    await update.message.reply_text(
                        "Error saving drink. Please try again.",
                        reply_markup=remove_keyboard()
                    )
            else:
                await update.message.reply_text(
                    "Please select volume from the menu:",
                    reply_markup=get_drink_volumes_keyboard()
                )
        
        # Custom volume input
        elif state == 'awaiting_custom_volume':
            try:
                volume_ml = int(text)
                if volume_ml < 1 or volume_ml > 5000:
                    await update.message.reply_text("Please enter a valid volume (1-5000 ml):")
                    return
                
                data = self.user_manager.get_user_data(user_id)
                drink_name = data['drink_name']
                
                drink_info = self.drink_manager.get_drink_nutrition(drink_name, volume_ml)
                
                drink_data = {
                    'user_id': user_id,
                    'drink_name': drink_name,
                    'volume_ml': volume_ml,
                    'calories': drink_info['calories'],
                    'protein': drink_info['protein'],
                    'fat': drink_info['fat'],
                    'carbs': drink_info['carbs'],
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
                if self.db.save_drink(drink_data):
                    await update.message.reply_html(
                        f"<b>Drink saved!</b>\n\n"
                        f"{drink_name} ({volume_ml}ml)\n\n"
                        f"<b>Nutrition:</b>\n"
                        f"Calories: <b>{drink_info['calories']:.0f} kcal</b>\n"
                        f"Protein: <b>{drink_info['protein']:.1f} g</b>\n"
                        f"Fat: <b>{drink_info['fat']:.1f} g</b>\n"
                        f"Carbs: <b>{drink_info['carbs']:.1f} g</b>",
                        reply_markup=remove_keyboard()
                    )
                    self.user_manager.set_user_state(user_id, 'main_menu')
                else:
                    await update.message.reply_text("Error saving drink.")
            except ValueError:
                await update.message.reply_text("Please enter a valid number:")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        state = self.user_manager.get_user_state(user_id)
        
        if state == 'awaiting_food_photo':
            await update.message.reply_text("Analyzing photo...")
            
            # Get the largest photo
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Recognize food
            result = self.vision.detect_food_items(bytes(photo_bytes))
            
            if result['success'] and result['items']:
                items_text = "\n".join([
                    f"• {item['name']} (confidence: {item['confidence']*100:.0f}%)"
                    for item in result['items'][:5]
                ])
                
                # For simplicity, we'll ask user to input weights
                # In production, you'd integrate portion size estimation
                
                data = self.user_manager.get_user_data(user_id)
                data['recognized_items'] = result['items'][:5]
                self.user_manager.set_user_state(user_id, 'awaiting_manual_input', data)
                
                await update.message.reply_html(
                    f"<b>Recognized:</b>\n\n"
                    f"{items_text}\n\n"
                    f"Please enter the weights for each item.\n\n"
                    f"Format: food name - weight in grams\n"
                    f"Example:\n"
                    f"Chicken - 150\n"
                    f"Rice - 100",
                    reply_markup=remove_keyboard()
                )
            else:
                await update.message.reply_text(
                    "Could not recognize food in the photo.\n\n"
                    "Please enter food items manually.\n\n"
                    "Format: food name - weight in grams\n"
                    "Example:\n"
                    "Chicken - 150\n"
                    "Rice - 100",
                    reply_markup=remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'awaiting_manual_input')
        else:
            await update.message.reply_text("Please use /add_meal to start adding a meal.")
    
    # Commands
    async def add_meal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "Select meal type:",
            reply_markup=get_meal_type_keyboard()
        )
        self.user_manager.set_user_state(user_id, 'awaiting_meal_type')
    
    async def add_drink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "Enter drink name (e.g., Cola, Coffee, Orange Juice):",
            reply_markup=remove_keyboard()
        )
        self.user_manager.set_user_state(user_id, 'awaiting_drink_name')
    
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        remaining = self.calculator.get_remaining_cpfc(
            user_id,
            datetime.now().strftime('%Y-%m-%d')
        )
        
        if remaining:
            progress_calories = (remaining['consumed_calories'] / remaining['target_calories']) * 100 if remaining['target_calories'] > 0 else 0
            progress_protein = (remaining['consumed_protein'] / remaining['target_protein']) * 100 if remaining['target_protein'] > 0 else 0
            progress_fat = (remaining['consumed_fat'] / remaining['target_fat']) * 100 if remaining['target_fat'] > 0 else 0
            progress_carbs = (remaining['consumed_carbs'] / remaining['target_carbs']) * 100 if remaining['target_carbs'] > 0 else 0
            
            await update.message.reply_html(
                f"<b>Today's Summary</b>\n\n"
                f"<b>Consumed / Target:</b>\n\n"
                f"Calories: <b>{remaining['consumed_calories']:.0f}</b> / {remaining['target_calories']:.0f} kcal ({progress_calories:.0f}%)\n"
                f"Protein: <b>{remaining['consumed_protein']:.0f}</b> / {remaining['target_protein']:.0f} g ({progress_protein:.0f}%)\n"
                f"Fat: <b>{remaining['consumed_fat']:.0f}</b> / {remaining['target_fat']:.0f} g ({progress_fat:.0f}%)\n"
                f"Carbs: <b>{remaining['consumed_carbs']:.0f}</b> / {remaining['target_carbs']:.0f} g ({progress_carbs:.0f}%)\n\n"
                f"<b>Remaining:</b>\n\n"
                f"Calories: <b>{remaining['remaining_calories']:.0f} kcal</b>\n"
                f"Protein: <b>{remaining['remaining_protein']:.0f} g</b>\n"
                f"Fat: <b>{remaining['remaining_fat']:.0f} g</b>\n"
                f"Carbs: <b>{remaining['remaining_carbs']:.0f} g</b>"
            )
        else:
            await update.message.reply_text(
                "Please complete your profile first using /start"
            )
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        profile = self.db.get_user_profile(user_id)
        
        if profile:
            activity_names = {
                'sedentary': 'Sedentary',
                'light': 'Light',
                'medium': 'Moderate',
                'active': 'Active',
                'very_active': 'Very Active'
            }
            
            goal_names = {
                'weight_loss': 'Weight Loss',
                'maintenance': 'Maintenance',
                'weight_gain': 'Weight Gain'
            }
            
            await update.message.reply_html(
                f"<b>Your Profile</b>\n\n"
                f"Height: <b>{profile.get('height', 'Not set')} cm</b>\n"
                f"Weight: <b>{profile.get('weight', 'Not set')} kg</b>\n"
                f"Age: <b>{profile.get('age', 'Not set')}</b>\n"
                f"Gender: <b>{profile.get('gender', 'Not set').title()}</b>\n"
                f"Activity: <b>{activity_names.get(profile.get('activity_level'), 'Not set')}</b>\n"
                f"Goal: <b>{goal_names.get(profile.get('goal'), 'Not set')}</b>\n\n"
                f"<b>Daily Target:</b>\n"
                f"Calories: <b>{profile.get('daily_calories', 0):.0f} kcal</b>"
            )
        else:
            await update.message.reply_text(
                "Profile not found. Please complete registration using /start"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(
            "<b>Available Commands:</b>\n\n"
            "/start - Start/Restart bot\n"
            "/add_meal - Add meal\n"
            "/add_drink - Add drink\n"
            "/today - Today's summary\n"
            "/profile - View profile\n"
            "/help - This help message\n\n"
            "<b>How it works:</b>\n\n"
            "1. Complete your profile\n"
            "2. Add meals by photo or manually\n"
            "3. Track your daily nutrition\n"
            "4. Achieve your goals!"
        )

def main():
    """Main function to run the bot"""
    bot = FithubBot()
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("add_meal", bot.add_meal_command))
    application.add_handler(CommandHandler("add_drink", bot.add_drink_command))
    application.add_handler(CommandHandler("today", bot.today_command))
    application.add_handler(CommandHandler("profile", bot.profile_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    
    # Start bot
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
