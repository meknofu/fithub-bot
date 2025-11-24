import logging

logger = logging.getLogger(__name__)

class DrinkManager:
    def __init__(self):
        self.drink_database = self._initialize_drink_database()
    
    def _initialize_drink_database(self):
        """Enhanced database of popular drinks"""
        return {
            # Water and low-calorie drinks
            'water': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'mineral water': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'sparkling water': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            'soda water': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
            
            # Juices
            'orange juice': {'calories': 45, 'protein': 0.7, 'fat': 0.2, 'carbs': 10.4},
            'apple juice': {'calories': 46, 'protein': 0.1, 'fat': 0.1, 'carbs': 11.7},
            'tomato juice': {'calories': 17, 'protein': 0.9, 'fat': 0.1, 'carbs': 3.6},
            'multifruit juice': {'calories': 48, 'protein': 0.4, 'fat': 0.1, 'carbs': 11.6},
            'grape juice': {'calories': 60, 'protein': 0.3, 'fat': 0.1, 'carbs': 14.8},
            
            # Carbonated drinks
            'cola': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'pepsi': {'calories': 41, 'protein': 0, 'fat': 0, 'carbs': 10.6},
            'sprite': {'calories': 40, 'protein': 0, 'fat': 0, 'carbs': 9.9},
            'fanta': {'calories': 46, 'protein': 0, 'fat': 0, 'carbs': 11.4},
            'lemonade': {'calories': 40, 'protein': 0, 'fat': 0, 'carbs': 10},
            
            # Energy drinks
            'red bull': {'calories': 45, 'protein': 0, 'fat': 0, 'carbs': 11},
            'monster': {'calories': 47, 'protein': 0, 'fat': 0, 'carbs': 11.5},
            'burn': {'calories': 43, 'protein': 0, 'fat': 0, 'carbs': 10.5},
            'adrenaline rush': {'calories': 48, 'protein': 0, 'fat': 0, 'carbs': 12},
            
            # Tea and coffee
            'black tea': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0.3},
            'green tea': {'calories': 1, 'protein': 0, 'fat': 0, 'carbs': 0},
            'black coffee': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'latte': {'calories': 54, 'protein': 3, 'fat': 2.4, 'carbs': 5.3},
            'cappuccino': {'calories': 38, 'protein': 2.1, 'fat': 1.5, 'carbs': 3.8},
            'americano': {'calories': 2, 'protein': 0.3, 'fat': 0, 'carbs': 0},
            'espresso': {'calories': 2, 'protein': 0.1, 'fat': 0, 'carbs': 0.4},
            
            # Milk and dairy drinks
            'whole milk': {'calories': 61, 'protein': 3.2, 'fat': 3.2, 'carbs': 4.7},
            'skim milk': {'calories': 34, 'protein': 3.4, 'fat': 0.1, 'carbs': 4.9},
            'almond milk': {'calories': 17, 'protein': 0.4, 'fat': 1.1, 'carbs': 1.5},
            'soy milk': {'calories': 33, 'protein': 2.9, 'fat': 1.6, 'carbs': 1.2},
            'oat milk': {'calories': 47, 'protein': 1, 'fat': 1.5, 'carbs': 7.6},
            'kefir': {'calories': 56, 'protein': 2.8, 'fat': 3.2, 'carbs': 4},
            'yogurt drink': {'calories': 55, 'protein': 2.9, 'fat': 1.5, 'carbs': 7.5},
            
            # Sports drinks
            'isotonic': {'calories': 27, 'protein': 0, 'fat': 0, 'carbs': 6.7},
            'gatorade': {'calories': 26, 'protein': 0, 'fat': 0, 'carbs': 6.5},
            'powerade': {'calories': 27, 'protein': 0, 'fat': 0, 'carbs': 6.8},
            
            # Alcohol
            'beer': {'calories': 43, 'protein': 0.5, 'fat': 0, 'carbs': 3.6},
            'light beer': {'calories': 29, 'protein': 0.2, 'fat': 0, 'carbs': 1.5},
            'wine red': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'wine white': {'calories': 82, 'protein': 0.1, 'fat': 0, 'carbs': 2.6},
            'champagne': {'calories': 76, 'protein': 0.2, 'fat': 0, 'carbs': 1.4},
            'vodka': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            'whiskey': {'calories': 250, 'protein': 0, 'fat': 0, 'carbs': 0},
            'rum': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            'gin': {'calories': 231, 'protein': 0, 'fat': 0, 'carbs': 0},
            
            # Cocktails
            'mojito': {'calories': 143, 'protein': 0.1, 'fat': 0, 'carbs': 13.8},
            'margarita': {'calories': 168, 'protein': 0.1, 'fat': 0, 'carbs': 13},
            'cosmopolitan': {'calories': 146, 'protein': 0, 'fat': 0, 'carbs': 13},
            'pina colada': {'calories': 245, 'protein': 0.6, 'fat': 2.9, 'carbs': 32}
        }
    
    def get_drink_nutrition(self, drink_name, volume_ml=100):
        """Get nutrition data for a drink"""
        drink_name_lower = drink_name.lower().strip()
        
        # Search in database
        if drink_name_lower in self.drink_database:
            base_nutrition = self.drink_database[drink_name_lower]
            multiplier = volume_ml / 100
            
            return {
                'drink_name': drink_name,
                'volume_ml': volume_ml,
                'calories': round(base_nutrition['calories'] * multiplier, 2),
                'protein': round(base_nutrition['protein'] * multiplier, 2),
                'fat': round(base_nutrition['fat'] * multiplier, 2),
                'carbs': round(base_nutrition['carbs'] * multiplier, 2)
            }
        
        # If not found, return None
        return None
    
    def search_drinks(self, query):
        """Search for drinks by partial name"""
        query_lower = query.lower().strip()
        results = []
        
        for drink_name in self.drink_database.keys():
            if query_lower in drink_name:
                results.append(drink_name.title())
        
        return results
    
    def get_popular_drinks(self):
        """Get list of popular drinks"""
        return [
            'Water', 'Cola', 'Orange Juice', 'Coffee', 'Tea',
            'Milk', 'Red Bull', 'Beer', 'Isotonic', 'Latte'
        ]
    
    def get_drink_categories(self):
        """Get drink categories"""
        return {
            'Water': ['water', 'mineral water', 'sparkling water'],
            'Soda': ['cola', 'pepsi', 'sprite', 'fanta', 'lemonade'],
            'Coffee/Tea': ['black coffee', 'latte', 'cappuccino', 'black tea', 'green tea'],
            'Juice': ['orange juice', 'apple juice', 'tomato juice', 'grape juice'],
            'Dairy Drink': ['milk', 'kefir', 'yogurt drink', 'almond milk', 'soy milk'],
            'Energy Drink': ['red bull', 'monster', 'burn'],
            'Sports Drink': ['isotonic', 'gatorade', 'powerade'],
            'Alcohol': ['beer', 'wine red', 'wine white', 'vodka', 'whiskey']
        }
