import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import Config
from database import db
from vision_api import VisionAPI
from cpfc_calculator import CPFCCalculator
from user_manager import UserManager
from drink_manager import DrinkManager
import re
from datetime import datetime

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
    
    def get_yes_no_keyboard(self):
        """Simple Yes/No keyboard"""
        return ReplyKeyboardMarkup([['Yes', 'No']], one_time_keyboard=True, resize_keyboard=True)
    
    def get_user_type_keyboard(self):
        """User type selection keyboard"""
        return ReplyKeyboardMarkup([['Trainer', 'Trainee']], one_time_keyboard=True, resize_keyboard=True)
    
    def get_meal_type_keyboard(self):
        """Meal type selection keyboard"""
        return ReplyKeyboardMarkup(
            [['Breakfast', 'Lunch'], ['Dinner', 'Snack']], 
            one_time_keyboard=True, 
            resize_keyboard=True
        )
    
    def get_drink_volumes_keyboard(self):
        """Drink volume selection keyboard"""
        return ReplyKeyboardMarkup([
            ['250ml (glass)', '330ml (can)'],
            ['500ml (bottle)', '1000ml (liter)'],
            ['Other']
        ], one_time_keyboard=True, resize_keyboard=True)
    
    def remove_keyboard(self):
        """Remove keyboard"""
        return ReplyKeyboardRemove()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            logger.info(f"User {user.id} started bot")
            
            existing_profile = self.db.get_user_profile(user.id)
            
            if existing_profile and existing_profile.get('height'):
                await update.message.reply_html(
                    f"Welcome back, {user.first_name}!\n\n"
                    f"Your profile is already set up.\n\n"
                    f"<b>Commands:</b>\n"
                    f"/add_meal - Add meal\n"
                    f"/add_drink - Add drink\n"
                    f"/today - Today's summary\n"
                    f"/profile - View profile\n"
                    f"/help - Help\n\n"
                    f"Want to start over? Type /restart",
                    reply_markup=self.remove_keyboard()
                )
                return
            
            await update.message.reply_html(
                f"Welcome to FITHUB!\n\n"
                f"Hi, {user.first_name}! I'm your personal nutrition assistant.\n\n"
                f"I will help you:\n"
                f"- Track your daily nutrition\n"
                f"- Calculate calories and macros\n"
                f"- Recognize food from photos\n"
                f"- Monitor your progress\n\n"
                f"Who are you?",
                reply_markup=self.get_user_type_keyboard()
            )
            
            self.user_manager.set_user_state(user.id, 'awaiting_user_type')
        except Exception as e:
            logger.error(f"Error in start command: {e}", exc_info=True)
            await update.message.reply_text("Sorry, an error occurred. Please try again.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages based on user state"""
        try:
            user_id = update.effective_user.id
            text = update.message.text
            
            if text.strip().startswith('/'):
                return
            
            state = self.user_manager.get_user_state(user_id)
            
            logger.info(f"User {user_id} in state {state} sent: {text}")
            
            if state == 'awaiting_user_type':
                await self.handle_user_type_selection(update, text)
            elif state == 'awaiting_height':
                await self.handle_height_input(update, text)
            elif state == 'awaiting_weight':
                await self.handle_weight_input(update, text)
            elif state == 'awaiting_age':
                await self.handle_age_input(update, text)
            elif state == 'awaiting_gender':
                await self.handle_gender_selection(update, text)
            elif state == 'awaiting_activity_level':
                await self.handle_activity_level_selection(update, text)
            elif state == 'awaiting_goal':
                await self.handle_goal_selection(update, text)
            elif state == 'awaiting_meal_type':
                await self.handle_meal_type_selection(update, text)
            elif state == 'awaiting_photo_confirmation':
                await self.handle_photo_confirmation(update, text)
            elif state == 'awaiting_manual_input':
                await self.handle_manual_food_input(update, text)
            elif state == 'awaiting_final_confirmation':
                await self.handle_final_confirmation(update, text)
            elif state == 'awaiting_drink_name':
                await self.handle_drink_name_input(update, text)
            elif state == 'awaiting_drink_volume':
                await self.handle_drink_volume_selection(update, text)
            elif state == 'awaiting_custom_volume':
                await self.handle_custom_volume_input(update, text)
            else:
                await update.message.reply_text(
                    "I didn't understand that. Use /help to see available commands."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, an error occurred. Please use /start to restart."
            )
    
    async def handle_user_type_selection(self, update: Update, text: str):
        """Handle user type selection"""
        user_id = update.effective_user.id
        
        if 'Trainer' in text:
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
                reply_markup=self.remove_keyboard()
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
                reply_markup=self.remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_height')
    
    async def handle_height_input(self, update: Update, text: str):
        """Handle height input"""
        user_id = update.effective_user.id
        try:
            height = float(text)
            if height < 100 or height > 250:
                await update.message.reply_text("Please enter a valid height (100-250 cm):")
                return
            
            self.user_manager.set_user_state(user_id, 'awaiting_weight', {'height': height})
            await update.message.reply_text(f"Height: {height} cm\n\nNow enter your weight in kg (e.g., 70):")
        except ValueError:
            await update.message.reply_text("Please enter a valid number:")
    
    async def handle_weight_input(self, update: Update, text: str):
        """Handle weight input"""
        user_id = update.effective_user.id
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
    
    async def handle_age_input(self, update: Update, text: str):
        """Handle age input"""
        user_id = update.effective_user.id
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
                reply_markup=ReplyKeyboardMarkup(
                    [['Male', 'Female']], 
                    one_time_keyboard=True, 
                    resize_keyboard=True
                )
            )
        except ValueError:
            await update.message.reply_text("Please enter a valid number:")
    
    async def handle_gender_selection(self, update: Update, text: str):
        """Handle gender selection"""
        user_id = update.effective_user.id
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
    
    async def handle_activity_level_selection(self, update: Update, text: str):
        """Handle activity level selection"""
        user_id = update.effective_user.id
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
    
    async def handle_goal_selection(self, update: Update, text: str):
        """Handle goal selection and complete profile setup"""
        user_id = update.effective_user.id
        goal_map = {
            'Weight Loss': 'weight_loss',
            'Maintenance': 'maintenance',
            'Weight Gain': 'weight_gain'
        }
        
        goal = goal_map.get(text)
        
        if goal:
            data = self.user_manager.get_user_data(user_id)
            data['goal'] = goal
            
            cpfc = self.calculator.calculate_daily_cpfc(
                weight=data['weight'],
                height=data['height'],
                age=data['age'],
                gender=data['gender'],
                activity_level=data['activity_level'],
                goal=goal
            )
            
            profile_data = {
                'height': data['height'],
                'weight': data['weight'],
                'age': data['age'],
                'gender': data['gender'],
                'activity_level': data['activity_level'],
                'goal': goal,
                'daily_calories': cpfc['calories']
            }
            
            success = self.db.update_user_profile(user_id, profile_data)
            logger.info(f"Profile update for user {user_id}: {success}")
            
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
                reply_markup=self.remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'main_menu')
        else:
            await update.message.reply_text("Please select a goal from the menu:")
    
    async def handle_meal_type_selection(self, update: Update, text: str):
        """Handle meal type selection"""
        user_id = update.effective_user.id
        if text in ['Breakfast', 'Lunch', 'Snack', 'Dinner']:
            data = self.user_manager.get_user_data(user_id)
            data['meal_type'] = text.lower()
            self.user_manager.set_user_state(user_id, 'awaiting_food_photo', data)
            await update.message.reply_text(
                f"Please send a photo of your {text.lower()}, or enter food items manually.\n\n"
                f"<b>Manual entry format:</b>\n"
                f"food name - weight in grams\n\n"
                f"<b>Example:</b>\n"
                f"Egg - 50\n"
                f"Carrot - 60\n"
                f"Orange - 130",
                reply_markup=self.remove_keyboard(),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "Please select a meal type:",
                reply_markup=self.get_meal_type_keyboard()
            )
    
    async def handle_photo_confirmation(self, update: Update, text: str):
        """Handle confirmation after photo recognition"""
        user_id = update.effective_user.id
        
        if text == 'Yes':
            # User accepts recognized items, proceed to save
            data = self.user_manager.get_user_data(user_id)
            recognized_items = data.get('recognized_items', [])
            
            # Convert recognized items to food_items format
            food_items = []
            for item in recognized_items:
                food_items.append({
                    'name': item['name'],
                    'weight': item.get('estimated_weight', 100)
                })
            
            # Show nutrition summary and ask for final confirmation
            await self.show_meal_summary_and_confirm(update, user_id, food_items)
            
        elif text == 'No':
            # User wants to manually adjust
            await update.message.reply_text(
                "Please enter the food items and weights manually.\n\n"
                "<b>Format:</b> food name - weight in grams\n\n"
                "<b>Example:</b>\n"
                "Egg - 50\n"
                "Carrot - 60\n"
                "Orange - 130",
                reply_markup=self.remove_keyboard(),
                parse_mode='HTML'
            )
            self.user_manager.set_user_state(user_id, 'awaiting_manual_input')
        else:
            await update.message.reply_text(
                "Please select Yes or No:",
                reply_markup=self.get_yes_no_keyboard()
            )
    
    async def handle_manual_food_input(self, update: Update, text: str):
        """Handle manual food input"""
        user_id = update.effective_user.id
        
        lines = text.strip().split('\n')
        food_items = []
        
        for line in lines:
            try:
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
                "Egg - 50\n"
                "Carrot - 60"
            )
            return
        
        # Show nutrition summary and ask for final confirmation
        await self.show_meal_summary_and_confirm(update, user_id, food_items)
    
    async def show_meal_summary_and_confirm(self, update, user_id, food_items):
        """Show meal summary with nutrition and ask for final confirmation"""
        meal_cpfc = self.calculator.calculate_meal_cpfc(food_items)
        
        if not meal_cpfc:
            meal_cpfc = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        
        items_text = "\n".join([f"- {item['name']}: {item['weight']}g" for item in food_items])
        
        data = self.user_manager.get_user_data(user_id)
        data['food_items'] = food_items
        data['total_calories'] = meal_cpfc['calories']
        data['total_protein'] = meal_cpfc['protein']
        data['total_fat'] = meal_cpfc['fat']
        data['total_carbs'] = meal_cpfc['carbs']
        
        self.user_manager.set_user_state(user_id, 'awaiting_final_confirmation', data)
        
        await update.message.reply_html(
            f"<b>Your meal:</b>\n\n"
            f"{items_text}\n\n"
            f"<b>Nutrition:</b>\n"
            f"Calories: <b>{meal_cpfc['calories']:.0f} kcal</b>\n"
            f"Protein: <b>{meal_cpfc['protein']:.0f} g</b>\n"
            f"Fat: <b>{meal_cpfc['fat']:.0f} g</b>\n"
            f"Carbs: <b>{meal_cpfc['carbs']:.0f} g</b>\n\n"
            f"<b>Save this meal?</b>",
            reply_markup=self.get_yes_no_keyboard()
        )
    
    async def handle_final_confirmation(self, update: Update, text: str):
        """Handle final meal save confirmation"""
        user_id = update.effective_user.id
        
        if text == 'Yes':
            data = self.user_manager.get_user_data(user_id)
            
            meal_data = {
                'user_id': user_id,
                'meal_type': data.get('meal_type', 'meal'),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'calories': data.get('total_calories', 0),
                'protein': data.get('total_protein', 0),
                'fat': data.get('total_fat', 0),
                'carbs': data.get('total_carbs', 0)
            }
            
            meal_id = self.db.save_meal(meal_data)
            logger.info(f"Meal saved for user {user_id}: meal_id={meal_id}")
            
            if meal_id:
                remaining = self.calculator.get_remaining_cpfc(
                    user_id,
                    datetime.now().strftime('%Y-%m-%d')
                )
                
                if remaining:
                    await update.message.reply_html(
                        f"<b>Meal saved successfully!</b>\n\n"
                        f"<b>Remaining for today:</b>\n\n"
                        f"Calories: <b>{remaining['remaining_calories']:.0f} kcal</b>\n"
                        f"Protein: <b>{remaining['remaining_protein']:.0f} g</b>\n"
                        f"Fat: <b>{remaining['remaining_fat']:.0f} g</b>\n"
                        f"Carbs: <b>{remaining['remaining_carbs']:.0f} g</b>\n\n"
                        f"Use /add_meal to add another meal or /today for full summary.",
                        reply_markup=self.remove_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        "Meal saved successfully!\n\nUse /add_meal to add another meal.",
                        reply_markup=self.remove_keyboard()
                    )
                
                self.user_manager.set_user_state(user_id, 'main_menu')
            else:
                await update.message.reply_text(
                    "Error saving meal. Please try again with /add_meal",
                    reply_markup=self.remove_keyboard()
                )
        
        elif text == 'No':
            await update.message.reply_text(
                "Meal cancelled. Use /add_meal to start over.",
                reply_markup=self.remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'main_menu')
        else:
            await update.message.reply_text(
                "Please select Yes or No:",
                reply_markup=self.get_yes_no_keyboard()
            )
    
    async def handle_drink_name_input(self, update: Update, text: str):
        """Handle drink name input"""
        user_id = update.effective_user.id
        drink_name = text.strip()
        
        drink_info = self.drink_manager.get_drink_nutrition(drink_name, 250)
        
        if drink_info:
            data = {'drink_name': drink_name, 'drink_info': drink_info}
            self.user_manager.set_user_state(user_id, 'awaiting_drink_volume', data)
            await update.message.reply_text(
                f"Found: {drink_name}\n\nSelect volume:",
                reply_markup=self.get_drink_volumes_keyboard()
            )
        else:
            similar = self.drink_manager.search_drinks(drink_name)
            
            if similar:
                await update.message.reply_text(
                    f"Drink '{drink_name}' not found.\n\n"
                    f"Did you mean:\n" + "\n".join(f"- {d}" for d in similar[:5]) + "\n\n"
                    f"Please enter the drink name again:",
                    reply_markup=self.remove_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"Drink '{drink_name}' not found in database.\n\n"
                    f"Please try another name or use /add_meal to log it as food.",
                    reply_markup=self.remove_keyboard()
                )
    
    async def handle_drink_volume_selection(self, update: Update, text: str):
        """Handle drink volume selection"""
        user_id = update.effective_user.id
        volume_ml = None
        
        if 'ml' in text or 'glass' in text or 'can' in text or 'bottle' in text or 'liter' in text:
            numbers = re.findall(r'\d+', text)
            if numbers:
                volume_ml = int(numbers[0])
        elif 'Other' in text:
            await update.message.reply_text(
                "Enter volume in ml (e.g., 350):",
                reply_markup=self.remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'awaiting_custom_volume')
            return
        
        if volume_ml:
            await self.save_drink(update, user_id, volume_ml)
        else:
            await update.message.reply_text(
                "Please select volume from the menu:",
                reply_markup=self.get_drink_volumes_keyboard()
            )
    
    async def handle_custom_volume_input(self, update: Update, text: str):
        """Handle custom volume input"""
        user_id = update.effective_user.id
        try:
            volume_ml = int(text)
            if volume_ml < 1 or volume_ml > 5000:
                await update.message.reply_text("Please enter a valid volume (1-5000 ml):")
                return
            
            await self.save_drink(update, user_id, volume_ml)
        except ValueError:
            await update.message.reply_text("Please enter a valid number:")
    
    async def save_drink(self, update, user_id, volume_ml):
        """Save drink to database"""
        data = self.user_manager.get_user_data(user_id)
        drink_name = data.get('drink_name', 'Unknown')
        
        drink_info = self.drink_manager.get_drink_nutrition(drink_name, volume_ml)
        
        if not drink_info:
            drink_info = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        
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
        
        logger.info(f"Saving drink for user {user_id}: {drink_data}")
        
        if self.db.save_drink(drink_data):
            await update.message.reply_html(
                f"<b>Drink saved!</b>\n\n"
                f"{drink_name} ({volume_ml}ml)\n\n"
                f"<b>Nutrition:</b>\n"
                f"Calories: <b>{drink_info['calories']:.0f} kcal</b>\n"
                f"Protein: <b>{drink_info['protein']:.1f} g</b>\n"
                f"Fat: <b>{drink_info['fat']:.1f} g</b>\n"
                f"Carbs: <b>{drink_info['carbs']:.1f} g</b>",
                reply_markup=self.remove_keyboard()
            )
            self.user_manager.set_user_state(user_id, 'main_menu')
        else:
            await update.message.reply_text(
                "Error saving drink. Please try again.",
                reply_markup=self.remove_keyboard()
            )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        user_id = update.effective_user.id
        state = self.user_manager.get_user_state(user_id)
        
        if state == 'awaiting_food_photo':
            await update.message.reply_text("Analyzing photo...")
            
            try:
                photo = update.message.photo[-1]
                photo_file = await photo.get_file()
                photo_bytes = await photo_file.download_as_bytearray()
                
                result = self.vision.detect_food_items(bytes(photo_bytes))
                
                if result['success'] and result['items']:
                    items_list = []
                    for item in result['items'][:10]:
                        name = item['name']
                        weight = item.get('estimated_weight', 100)
                        items_list.append(f"{name} - {weight}g")
                    
                    items_text = "\n".join(items_list)
                    
                    data = self.user_manager.get_user_data(user_id)
                    data['recognized_items'] = result['items'][:10]
                    self.user_manager.set_user_state(user_id, 'awaiting_photo_confirmation', data)
                    
                    await update.message.reply_html(
                        f"<b>Recognized with estimated weights:</b>\n\n"
                        f"{items_text}\n\n"
                        f"<b>Are these items and weights correct?</b>",
                        reply_markup=self.get_yes_no_keyboard()
                    )
                    
                else:
                    await update.message.reply_text(
                        "Could not recognize food in the photo.\n\n"
                        "Please enter food items manually.\n\n"
                        "Format: food name - weight in grams\n"
                        "Example:\n"
                        "Egg - 50\n"
                        "Carrot - 60",
                        reply_markup=self.remove_keyboard()
                    )
                    self.user_manager.set_user_state(user_id, 'awaiting_manual_input')
                    
            except Exception as e:
                logger.error(f"Error processing photo: {e}", exc_info=True)
                await update.message.reply_text(
                    "Error processing photo. Please enter food manually.",
                    reply_markup=self.remove_keyboard()
                )
                self.user_manager.set_user_state(user_id, 'awaiting_manual_input')
        else:
            await update.message.reply_text("Please use /add_meal to start adding a meal.")
    
    async def add_meal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_meal command"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "Select meal type:",
            reply_markup=self.get_meal_type_keyboard()
        )
        self.user_manager.set_user_state(user_id, 'awaiting_meal_type')
    
    async def add_drink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_drink command"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "Enter drink name (e.g., Cola, Coffee, Orange Juice):",
            reply_markup=self.remove_keyboard()
        )
        self.user_manager.set_user_state(user_id, 'awaiting_drink_name')
    
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /today command"""
        user_id = update.effective_user.id
        
        try:
            profile = self.db.get_user_profile(user_id)
            if not profile or not profile.get('daily_calories'):
                await update.message.reply_text(
                    "Please complete your profile first using /start"
                )
                return
            
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
                    "No data for today yet. Start tracking with /add_meal or /add_drink"
                )
        except Exception as e:
            logger.error(f"Error in today_command: {e}", exc_info=True)
            await update.message.reply_text("Error getting today's summary. Please try again.")
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        user_id = update.effective_user.id
        profile = self.db.get_user_profile(user_id)
        
        logger.info(f"Profile fetched for user {user_id}: {profile}")
        
        if profile and profile.get('height'):
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
                f"Gender: <b>{profile.get('gender', 'not set').title()}</b>\n"
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
        """Handle /help command"""
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
    try:
        logger.info("Starting bot initialization...")
        bot = FithubBot()
        logger.info("Bot instance created successfully")
        
        if not Config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set")
        
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set")
        
        application = Application.builder().token(Config.BOT_TOKEN).build()
        logger.info("Application builder configured")
        
        # Register command handlers BEFORE message handlers
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
        logger.info("Bot starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
