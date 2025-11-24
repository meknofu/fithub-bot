from google.cloud import vision
import io
import logging
import math
from config import Config

logger = logging.getLogger(__name__)

class VisionAPI:
    def __init__(self):
        try:
            if Config.GOOGLE_VISION_API_KEY:
                from google.cloud.vision_v1 import ImageAnnotatorClient
                from google.api_core.client_options import ClientOptions
                
                client_options = ClientOptions(api_key=Config.GOOGLE_VISION_API_KEY)
                self.client = ImageAnnotatorClient(client_options=client_options)
                logger.info("Google Vision API initialized with API Key")
            else:
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized with default credentials")
        except Exception as e:
            logger.error(f"Google Vision initialization failed: {e}")
            self.client = None
    
    def detect_food_items(self, image_content):
        """Enhanced food recognition with better item identification"""
        if not self.client:
            return self._get_fallback_response()
        
        try:
            image = vision.Image(content=image_content)
            
            # Get multiple types of analysis for better accuracy
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            
            # Web detection for better food identification
            web_response = self.client.web_detection(image=image)
            web_entities = web_response.web_detection.web_entities
            
            # Combine all sources for better recognition
            food_items = self._analyze_and_combine_results(objects, labels, web_entities)
            
            if not food_items:
                return self._get_fallback_response()
            
            # Estimate weights based on visual analysis
            food_items_with_weights = self._estimate_weights_for_items(food_items, image_content)
            
            return {
                'success': True,
                'items': food_items_with_weights,
                'confidence': self._calculate_average_confidence(food_items_with_weights)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()
    
    def _analyze_and_combine_results(self, objects, labels, web_entities):
        """Combine multiple detection sources for accurate food identification"""
        food_items = []
        seen_items = set()
        
        # Comprehensive food database for matching
        food_database = {
            # Proteins
            'egg': ['egg', 'boiled egg', 'hard boiled', 'soft boiled', 'eggs'],
            'chicken': ['chicken', 'chicken breast', 'poultry', 'grilled chicken'],
            'beef': ['beef', 'steak', 'meat', 'ground beef'],
            'fish': ['fish', 'salmon', 'tuna', 'seafood'],
            'pork': ['pork', 'bacon', 'ham', 'sausage'],
            
            # Vegetables
            'carrot': ['carrot', 'carrots', 'carrot stick'],
            'broccoli': ['broccoli', 'broccoli floret'],
            'tomato': ['tomato', 'tomatoes', 'cherry tomato'],
            'lettuce': ['lettuce', 'salad', 'leafy green', 'greens', 'salad greens'],
            'cucumber': ['cucumber', 'cucumbers'],
            'bell pepper': ['bell pepper', 'pepper', 'capsicum'],
            'spinach': ['spinach', 'leafy vegetable'],
            
            # Fruits
            'orange': ['orange', 'oranges', 'citrus', 'orange slice'],
            'apple': ['apple', 'apples'],
            'banana': ['banana', 'bananas'],
            'berry': ['berry', 'berries', 'strawberry', 'blueberry'],
            'grape': ['grape', 'grapes'],
            'watermelon': ['watermelon', 'melon'],
            
            # Grains & Carbs
            'rice': ['rice', 'white rice', 'brown rice', 'steamed rice'],
            'bread': ['bread', 'toast', 'slice of bread', 'baguette'],
            'pasta': ['pasta', 'noodles', 'spaghetti', 'macaroni'],
            'potato': ['potato', 'potatoes', 'baked potato'],
            'muffin': ['muffin', 'cupcake', 'baked good', 'breakfast muffin'],
            'oatmeal': ['oatmeal', 'oats', 'porridge'],
            
            # Dairy
            'cheese': ['cheese', 'cheddar', 'mozzarella'],
            'yogurt': ['yogurt', 'yoghurt'],
            'milk': ['milk', 'dairy'],
        }
        
        # Process web entities (most specific)
        for entity in web_entities[:10]:
            description = entity.description.lower()
            score = entity.score
            
            # Match against food database
            for food_name, keywords in food_database.items():
                if any(keyword in description for keyword in keywords):
                    if food_name not in seen_items and score > 0.3:
                        food_items.append({
                            'name': food_name.title(),
                            'confidence': score,
                            'source': 'web_entity'
                        })
                        seen_items.add(food_name)
                        break
        
        # Process object localization
        for obj in objects:
            name = obj.name.lower()
            
            for food_name, keywords in food_database.items():
                if any(keyword in name for keyword in keywords):
                    if food_name not in seen_items and obj.score > 0.5:
                        food_items.append({
                            'name': food_name.title(),
                            'confidence': obj.score,
                            'source': 'object',
                            'bounding_box': self._get_bounding_box_size(obj.bounding_poly)
                        })
                        seen_items.add(food_name)
                        break
        
        # Process labels (fallback)
        for label in labels[:15]:
            description = label.description.lower()
            
            for food_name, keywords in food_database.items():
                if any(keyword in description for keyword in keywords):
                    if food_name not in seen_items and label.score > 0.6:
                        food_items.append({
                            'name': food_name.title(),
                            'confidence': label.score,
                            'source': 'label'
                        })
                        seen_items.add(food_name)
                        break
        
        return food_items
    
    def _get_bounding_box_size(self, bounding_poly):
        """Calculate relative size of bounding box"""
        vertices = bounding_poly.normalized_vertices
        if len(vertices) >= 2:
            width = abs(vertices[1].x - vertices[0].x)
            height = abs(vertices[2].y - vertices[0].y) if len(vertices) > 2 else 0
            area = width * height
            return {'width': width, 'height': height, 'area': area}
        return None
    
    def _estimate_weights_for_items(self, food_items, image_content):
        """Estimate weights based on visual size and typical portions"""
        
        # Standard portion weights (in grams)
        standard_portions = {
            'egg': 50,  # One large egg
            'carrot': 60,  # Medium carrot stick
            'orange': 130,  # Medium orange slice (1/4 of whole)
            'lettuce': 30,  # Small handful
            'muffin': 80,  # Medium muffin
            'chicken': 150,  # Standard serving
            'beef': 150,
            'fish': 150,
            'rice': 150,  # Cooked rice serving
            'bread': 30,  # One slice
            'pasta': 180,  # Cooked pasta serving
            'broccoli': 85,
            'tomato': 100,
            'apple': 150,
            'banana': 120,
            'potato': 150,
            'cheese': 30,
            'yogurt': 150,
        }
        
        # Add estimated weights to items
        for item in food_items:
            food_name = item['name'].lower()
            base_weight = standard_portions.get(food_name, 100)
            
            # Adjust based on bounding box size if available
            if 'bounding_box' in item and item['bounding_box']:
                size_multiplier = self._calculate_size_multiplier(item['bounding_box'])
                estimated_weight = int(base_weight * size_multiplier)
            else:
                # Use count heuristic if multiple items detected
                count = self._estimate_item_count(item, food_items)
                estimated_weight = int(base_weight * count)
            
            # Clamp to reasonable range
            item['estimated_weight'] = max(20, min(500, estimated_weight))
        
        return food_items
    
    def _calculate_size_multiplier(self, bounding_box):
        """Calculate size multiplier based on bounding box area"""
        area = bounding_box.get('area', 0.1)
        
        # Typical food item on plate occupies 0.05-0.20 of image
        if area < 0.03:
            return 0.5  # Small portion
        elif area < 0.08:
            return 1.0  # Standard portion
        elif area < 0.15:
            return 1.5  # Large portion
        else:
            return 2.0  # Very large portion
    
    def _estimate_item_count(self, current_item, all_items):
        """Estimate how many of this item are present"""
        food_name = current_item['name'].lower()
        
        # Count how many times this food appears in detection
        count = sum(1 for item in all_items if item['name'].lower() == food_name)
        
        # Special cases
        if 'egg' in food_name:
            # Eggs often come in multiples (2-4 typical)
            return min(count, 4)
        elif any(fruit in food_name for fruit in ['orange', 'apple', 'banana']):
            # Fruit slices
            return min(count, 6)
        elif 'carrot' in food_name:
            # Carrot sticks
            return min(count, 8)
        
        return max(1, count)
    
    def _calculate_average_confidence(self, items):
        """Calculate average confidence score"""
        if not items:
            return 0
        total_confidence = sum(item['confidence'] for item in items)
        return total_confidence / len(items)
    
    def _get_fallback_response(self):
        """Fallback response when recognition fails"""
        return {
            'success': False,
            'items': [],
            'confidence': 0,
            'message': 'Could not recognize food items. Please enter manually.'
        }

# Test function for debugging
def test_vision_api():
    """Test function to verify Vision API setup"""
    vision_api = VisionAPI()
    
    if not vision_api.client:
        print("❌ Vision API not initialized. Check your GOOGLE_VISION_API_KEY")
        return False
    
    print("✅ Vision API initialized successfully")
    return True
