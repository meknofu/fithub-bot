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
        """Main function for food recognition"""
        if not self.client:
            return self._get_fallback_response()
        
        try:
            image = vision.Image(content=image_content)
            
            # Get different types of analysis
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            
            # Analyze results
            food_items = self._analyze_food_objects(objects, labels)
            
            if not food_items:
                return self._get_fallback_response()
            
            return {
                'success': True,
                'items': food_items,
                'confidence': self._calculate_average_confidence(food_items)
            }
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return self._get_fallback_response()
    
    def _analyze_food_objects(self, objects, labels):
        """Analyze detected objects and labels"""
        food_items = []
        food_keywords = [
            'food', 'dish', 'meal', 'plate', 'fruit', 'vegetable',
            'meat', 'fish', 'bread', 'salad', 'soup', 'dessert',
            'drink', 'beverage', 'snack', 'breakfast', 'lunch', 'dinner'
        ]
        
        # Process objects
        for obj in objects:
            name = obj.name.lower()
            if any(keyword in name for keyword in food_keywords) or self._is_food_item(name):
                food_items.append({
                    'name': obj.name,
                    'confidence': obj.score,
                    'type': 'object'
                })
        
        # Process labels if no objects found
        if not food_items:
            for label in labels[:10]:  # Top 10 labels
                name = label.description.lower()
                if any(keyword in name for keyword in food_keywords) or self._is_food_item(name):
                    food_items.append({
                        'name': label.description,
                        'confidence': label.score,
                        'type': 'label'
                    })
        
        return food_items
    
    def _is_food_item(self, name):
        """Check if item name is food-related"""
        food_categories = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna',
            'rice', 'pasta', 'potato', 'tomato', 'cucumber', 'lettuce',
            'apple', 'banana', 'orange', 'grape', 'berry',
            'cheese', 'egg', 'milk', 'yogurt', 'butter',
            'bread', 'cake', 'cookie', 'pie', 'chocolate'
        ]
        return any(category in name for category in food_categories)
    
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
    
    def detect_reference_object(self, image_content, reference_type='fork'):
        """Detect reference object for size estimation"""
        if not self.client:
            return None
        
        try:
            image = vision.Image(content=image_content)
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            # Standard sizes in cm
            reference_sizes = {
                'fork': 20,
                'spoon': 18,
                'phone': 15,
                'card': 8.5,
                'palm': 18
            }
            
            for obj in objects:
                if reference_type.lower() in obj.name.lower():
                    # Get bounding box
                    vertices = obj.bounding_poly.normalized_vertices
                    width = abs(vertices[1].x - vertices[0].x)
                    height = abs(vertices[2].y - vertices[0].y)
                    
                    # Estimate size
                    pixel_size = math.sqrt(width**2 + height**2)
                    real_size = reference_sizes.get(reference_type, 15)
                    
                    return {
                        'found': True,
                        'type': reference_type,
                        'pixel_size': pixel_size,
                        'real_size_cm': real_size,
                        'scale_factor': real_size / pixel_size if pixel_size > 0 else 1
                    }
            
            return {'found': False}
            
        except Exception as e:
            logger.error(f"Reference object detection error: {e}")
            return None
    
    def estimate_portion_size(self, image_content, food_item, reference_object=None):
        """Estimate portion size based on reference object"""
        if not self.client or not reference_object or not reference_object.get('found'):
            return self._get_default_portion()
        
        try:
            image = vision.Image(content=image_content)
            objects_response = self.client.object_localization(image=image)
            objects = objects_response.localized_object_annotations
            
            for obj in objects:
                if food_item.lower() in obj.name.lower():
                    vertices = obj.bounding_poly.normalized_vertices
                    width = abs(vertices[1].x - vertices[0].x)
                    height = abs(vertices[2].y - vertices[0].y)
                    
                    pixel_size = math.sqrt(width**2 + height**2)
                    scale_factor = reference_object.get('scale_factor', 1)
                    estimated_size_cm = pixel_size * scale_factor
                    
                    # Rough weight estimation (very approximate)
                    estimated_weight = self._estimate_weight_from_size(food_item, estimated_size_cm)
                    
                    return {
                        'estimated': True,
                        'size_cm': round(estimated_size_cm, 1),
                        'weight_grams': estimated_weight
                    }
            
            return self._get_default_portion()
            
        except Exception as e:
            logger.error(f"Portion size estimation error: {e}")
            return self._get_default_portion()
    
    def _estimate_weight_from_size(self, food_item, size_cm):
        """Rough weight estimation based on size (very approximate)"""
        # This is a very rough estimation and should be improved
        density_factors = {
            'default': 50,
            'bread': 30,
            'meat': 70,
            'vegetable': 40,
            'fruit': 45
        }
        
        food_lower = food_item.lower()
        factor = density_factors['default']
        
        for category, value in density_factors.items():
            if category in food_lower:
                factor = value
                break
        
        # Very rough calculation: size^2 * density factor
        estimated_weight = (size_cm ** 2) * factor / 10
        return round(max(50, min(500, estimated_weight)), 0)  # Between 50-500g
    
    def _get_default_portion(self):
        """Default portion when estimation fails"""
        return {
            'estimated': False,
            'size_cm': 0,
            'weight_grams': 100  # Default 100g
        }
