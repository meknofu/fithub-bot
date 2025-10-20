from dataclasses import dataclass
from typing import Optional, List

@dataclass
class User:
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    user_type: str  # 'trainer' or 'trainee'
    height: Optional[float]
    weight: Optional[float]
    daily_calories: Optional[float]
    trainer_id: Optional[int]

@dataclass
class FoodItem:
    name: str
    calories: float
    protein: float
    fat: float
    carbs: float

@dataclass
class Meal:
    food_items: List[FoodItem]
    total_weight: float
    calories: float
    protein: float
    fat: float
    carbs: float

@dataclass
class DailyIntake:
    date: str
    meals: List[Meal]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
