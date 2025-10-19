# Создайте convert.py
import json

with open('google_vision_credentials.json', 'r') as f:
    data = json.load(f)

print("Скопируйте эту строку в Railway:")
print(json.dumps(data))
