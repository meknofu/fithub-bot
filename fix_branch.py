import subprocess
import os

def run_cmd(command):
    print(f"🔧 Выполняю: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Успех: {result.stdout.strip()}")
    else:
        print(f"❌ Ошибка: {result.stderr.strip()}")
    return result.returncode == 0, result.stdout, result.stderr

def main():
    print("🎯 РЕШЕНИЕ ОШИБКИ BRANCH")
    print("=" * 50)
    
    # Проверяем текущие ветки
    print("1. 📊 ПРОВЕРКА ВЕТОК:")
    success, stdout, stderr = run_cmd("git branch -a")
    
    if "master" in stdout:
        print("\n✅ Найдена ветка 'master'")
        # Переименовываем master в main
        run_cmd("git branch -M master main")
        run_cmd("git push -u origin main")
        
    elif "main" in stdout:
        print("\n✅ Ветка 'main' уже существует")
        run_cmd("git push -u origin main")
        
    else:
        print("\n❌ Ветки не найдены. Создаем коммит...")
        # Создаем первый коммит
        run_cmd("git add .")
        run_cmd('git commit -m "Fithub Bot with Google Vision API"')
        run_cmd("git branch -M main")
        run_cmd("git push -u origin main")
    
    print("\n🎉 ПРОВЕРКА РЕЗУЛЬТАТА:")
    run_cmd("git branch -a")
    run_cmd("git remote -v")

if __name__ == '__main__':
    main()
