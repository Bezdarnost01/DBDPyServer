import os
import sqlite3

# Абсолютный путь к базе
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "data", "SESSIONS.db")

print("1. Абсолютный путь к БД:", db_path)

print("2. Проверка существования файла...")
print("  Существует:", os.path.isfile(db_path))
print("  Чтение:", os.access(db_path, os.R_OK))
print("  Запись:", os.access(db_path, os.W_OK))

print("3. Текущая рабочая директория:", os.getcwd())

if not os.path.isfile(db_path):
    print("Файл базы данных не найден!")
    exit(1)

print("\n4. Соединяемся через sqlite3...")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("5. SHOW TABLES:")
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("  Таблицы:", tables)
except Exception as e:
    print("  Ошибка при получении таблиц:", e)

if ('sessions',) in tables:
    print("\n6. Схема таблицы 'sessions':")
    try:
        cur.execute("PRAGMA table_info(sessions);")
        for col in cur.fetchall():
            print(col)
    except Exception as e:
        print("  Ошибка при получении схемы:", e)
else:
    print("\n6. Таблица 'sessions' НЕ найдена.")

cur.close()
conn.close()
print("\nПроверка завершена!")
