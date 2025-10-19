import subprocess
import os

def run_cmd(command):
    print(f"🔧 {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {result.stdout.strip()}")
        return True, result.stdout
    else:
        print(f"❌ {result.stderr.strip()}")
        return False, result.stderr

def main():
    print("🎯 СОЗДАНИЕ ВЕТКИ MAIN")
    print("=" * 50)
    
    # Проверяем текущую ветку
    print("1. Проверяем текущие ветки:")
    success, output = run_cmd("git branch -a")
    
    # Создаем коммит если нет коммитов
    print("\n2. Создаем коммит:")
    run_cmd("git add .")
    run_cmd('git commit -m "Fithub Bot Deployment"')
    
    # Создаем ветку main
    print("\n3. Создаем ветку main:")
    run_cmd("git branch -M main")
    
    # Пушим
    print("\n4. Пушим на GitHub:")
    success, output = run_cmd("git push -u origin main")
    
    if not success:
        print("\n🔄 Пробуем принудительный пуш:")
        run_cmd("git push -u origin main --force")
    
    print("\n📊 ФИНАЛЬНЫЙ СТАТУС:")
    run_cmd("git branch -a")
    run_cmd("git status")

if __name__ == '__main__':
    main()
