import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import Config
from database import db
from vision_api import VisionAPI
from cpfc_calculator import CPFCCalculator
from user_manager import UserManager
from drink_manager import DrinkManager
from keyboards import (
    get_user_type_keyboard,
    get_confirm_keyboard,
    get_meal_type_keyboard,
    get_yes_no_keyboard,
    get_drink_method_keyboard,
    get_drink_categories_keyboard,
    get_popular_drinks_keyboard,
    get_drink_volumes_keyboard,
    get_reference_object_keyboard,
    remove_keyboard
)
import io
import re
from datetime import datetime

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class FithubBot:
    def __init__(self):
        try:
            self.db = db
            logger.info("Database initialized")
            
            self.vision = VisionAPI()
            logger.info("Vision API initialized")
            
            self.calculator = CPFCCalculator()
            logger.info("CPFC Calculator initialized")
            
            self.user_manager = UserManager()
            logger.info("User Manager initialized")
            
            self.drink_manager = DrinkManager()
            logger.info("Drink Manager initialized")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            user_data = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            
            await update.message.reply_html(
                f"👋 Welcome to FITHUB!\n\n"
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
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Sorry, an error occurred. Please try again.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            text = update.message.text
            state = self.user_manager.get_user_state(user_id)
            
            logger.info(f"User {user_id} in state {state} sent: {text}")
            
            # User type selection
            if state == 'awaiting_user_type':
                if 'Trainer' in text:
                    self.db.save_user({
                        'id': user_id,
                        'username': update.effective_user.username,
                        'first_name': update.effective_user.first_name,
                        'last_name': update.effective_user.last_name,
                        'user_type': 'trainer'
                    })
                    await update.message.reply_text(
                        "👨‍🏫 You are registered as a Trainer!\n\n"
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
                        "🏃 You are registered as a Trainee!\n\n"
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
                    await update.message.reply_text(f"✅ Height: {height} cm\n\nNow enter your weight in kg (e.g., 70):")
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
                    await update.message.reply_text(f"✅ Weight: {weight} kg\n\nNow enter your age (e.g., 25):")
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
                        f"✅ Age: {age}\n\nSelect your gender:",
                        reply_markup=ReplyKeyboardMarkup(
                            [['Male', 'Female']], 
                            one_time_keyboard=True, 
                            resize_keyboard=True
                        )
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
                        f"✅ Gender: {text}\n\nSelect your activity level:",
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
                        f"✅ Activity level set\n\nSelect your goal:",
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
                        f"✅ <b>Profile completed!</b>\n\n"
                        f"📊 <b>Your personalized nutrition plan:</b>\n\n"
                        f"🔥 Calories: <b>{cpfc['calories']:.0f} kcal/day</b>\n"
                        f"🥩 Protein: <b>{cpfc['protein']:.0f} g/day</b>\n"
                        f"🥑 Fat: <b>{cpfc['fat']:.0f} g/day</b>\n"
                        f"🍞 Carbs: <b>{cpfc['carbs']:.0f} g/day</b>\n\n"
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
            
            # [Rest of your handle_message code continues here - keeping the same structure]
            # For brevity, I'm showing the pattern - you'd continue with all other states
            
        except Exception as e:
            logger.error(f"Error in handle_message: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, an error occurred processing your message. Please try again or use /start to restart."
            )
    
    # [Rest of your methods with try-except blocks added]

def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting bot initialization...")
        bot = FithubBot()
        logger.info("Bot instance created successfully")
        
        # Verify config
        if not Config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set in environment variables")
        
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in environment variables")
        
        # Create application
        application = Application.builder().token(Config.BOT_TOKEN).build()
        logger.info("Application builder configured")
        
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
        
        logger.info("All handlers registered")
        
        # Start bot
        logger.info("Bot starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
