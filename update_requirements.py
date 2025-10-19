def create_stable_requirements():
    """Создает стабильную версию requirements.txt"""
    content = """python-telegram-bot==20.7
requests==2.31.0
python-dotenv==1.0.0
pillow==10.0.1
google-cloud-vision==3.4.1
"""
    
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ requirements.txt обновлен!")
    print("📋 Новое содержимое:")
    print(content)

if __name__ == '__main__':
    create_stable_requirements()
