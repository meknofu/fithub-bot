import logging

logger = logging.getLogger(__name__)

class DrinkManager:
    def __init__(self):
        # Comprehensive drink database (per 100ml)
        self.drinks_db = {
            'water': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'cola': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'coke': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'pepsi': {'calories': 41, 'protein': 0, 'fat': 0, 'carbs': 11},
            'sprite': {'calories': 39, 'protein': 0, 'fat': 0, 'carbs': 10},
            '7up': {'calories': 38, 'protein': 0, 'fat': 0, 'carbs': 10},
            'fanta': {'calories': 45, 'protein': 0, 'fat': 0, 'carbs': 12},
            
            # Coffee & Tea
            'coffee': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'black coffee': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'latte': {'calories': 54, 'protein': 3.4, 'fat': 2, 'carbs': 5.5},
            'cappuccino': {'calories': 38, 'protein': 2.5, 'fat': 1.5, 'carbs': 4},
            'espresso': {'calories': 9, 'protein': 0.5, 'fat': 0.2, 'carbs': 1.6},
            'tea': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0.3},
            'green tea': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'black tea': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0.3},
            
            # Juice
            'orange juice': {'calories': 45, 'protein': 0.7, 'fat': 0.2, 'carbs': 10.4},
            'apple juice': {'calories': 46, 'protein': 0.1, 'fat': 0.1, 'carbs': 11.3},
            'grape juice': {'calories': 60, 'protein': 0.4, 'fat': 0.1, 'carbs': 14.8},
            'pineapple juice': {'calories': 53, 'protein': 0.4, 'fat': 0.1, 'carbs': 12.9},
            'tomato juice': {'calories': 17, 'protein': 0.8, 'fat': 0.1, 'carbs': 3.9},
            'cranberry juice': {'calories': 46, 'protein': 0, 'fat': 0.1, 'carbs': 12.2},
            
            # Milk & Dairy
            'milk': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 4.7},
            'whole milk': {'calories': 61, 'protein': 3.2, 'fat': 3.3, 'carbs': 4.8},
            'skim milk': {'calories': 34, 'protein': 3.4, 'fat': 0.1, 'carbs': 5},
            'almond milk': {'calories': 13, 'protein': 0.4, 'fat': 1.1, 'carbs': 0.6},
            'soy milk': {'calories': 33, 'protein': 2.9, 'fat': 1.6, 'carbs': 1.5},
            'oat milk': {'calories': 47, 'protein': 1, 'fat': 1.5, 'carbs': 7.6},
            
            # Energy & Sports Drinks
            'red bull': {'calories': 45, 'protein': 0, 'fat': 0, 'carbs': 11},
            'monster': {'calories': 47, 'protein': 0, 'fat': 0, 'carbs': 12},
            'gatorade': {'calories': 25, 'protein': 0, 'fat': 0, 'carbs': 6},
            'powerade': {'calories': 27, 'protein': 0, 'fat': 0, 'carbs': 7},
            
            # Alcohol
            'beer': {'calories': 43, 'protein': 0.5, 'fat': 0, 'carbs': 3.6},
            'wine': {'calories': 83, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'vodka': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            'whiskey': {'calories': 250, 'protein': 0, 'fat': 0, 'carbs': 0},
            
            # Smoothies & Shakes
            'protein shake': {'calories': 80, 'protein': 16, 'fat': 1, 'carbs': 3},
            'smoothie': {'calories': 60, 'protein': 1, 'fat': 0.5, 'carbs': 14},
            'milkshake': {'calories': 112, 'protein': 3.5, 'fat': 3.5, 'carbs': 17}
        }
    
    def get_drink_nutrition(self, drink_name, volume_ml):
        """
        Get nutrition for a drink based on volume.
        Returns TOTAL nutrition for the given volume (not per 100ml).
        """
        drink_lower = drink_name.lower().strip()
        
        # Find drink in database
        if drink_lower in self.drinks_db:
            per_100ml = self.drinks_db[drink_lower]
        else:
            # Try partial match
            found = False
            for key in self.drinks_db:
                if key in drink_lower or drink_lower in key:
                    per_100ml = self.drinks_db[key]
                    found = True
                    logger.info(f"Partial match: '{drink_name}' matched to '{key}'")
                    break
            
            if not found:
                logger.warning(f"Drink '{drink_name}' not found in database")
                return None
        
        # Calculate for actual volume
        ratio = volume_ml / 100
        
        result = {
            'calories': round(per_100ml['calories'] * ratio, 1),
            'protein': round(per_100ml['protein'] * ratio, 1),
            'fat': round(per_100ml['fat'] * ratio, 1),
            'carbs': round(per_100ml['carbs'] * ratio, 1),
            'drink_name': drink_name,
            'volume_ml': volume_ml
        }
        
        logger.info(f"Drink nutrition for {drink_name} ({volume_ml}ml): {result}")
        return result
    
    def search_drinks(self, query):
        """Search for drinks by name"""
        query_lower = query.lower().strip()
        matches = []
        
        for drink_name in self.drinks_db.keys():
            if query_lower in drink_name or drink_name in query_lower:
                matches.append(drink_name.title())
        
        return matches[:10]  # Return max 10 matches
