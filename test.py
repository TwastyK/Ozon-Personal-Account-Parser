import json
import os

def deep_search_status(data, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            # Ищем ключи, связанные со статусом или состоянием
            if any(word in k.lower() for word in ["status", "state", "tracking"]):
                print(f"Путь: {path}.{k}")
                print(f"Значение: {v}")
                print("-" * 40)
            deep_search_status(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            deep_search_status(item, f"{path}[{i}]")

# Указываем правильный путь к файлу внутри папки debug_json
file_path = os.path.join("debug_json", "details_65798.json")

try:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"[*] Сканирую {file_path} на наличие системных статусов...")
    deep_search_status(raw_data)
except FileNotFoundError:
    print(f"[-] Файл не найден по пути: {file_path}")