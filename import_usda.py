import pandas as pd
import psycopg2
from config import Config
import requests
import io

def import_usda_data():
    """Импортирует данные USDA в базу данных"""
    conn = psyc
