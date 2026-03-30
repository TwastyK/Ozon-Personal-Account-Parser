import os
import json
import asyncio
import shutil
import time
import random

from collector import collect_data
from processor import extract_all_data
import notifier

CHECK_INTERVAL = (1, 1)
INPUT_DIR = "debug_json"


async def run_iteration():
    print(f"\n[{time.strftime('%H:%M:%S')}] --- СТАРТ ПРОВЕРКИ ---")

    await collect_data()

    current_results = []
    if os.path.exists(INPUT_DIR) and os.listdir(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("details")]

        for filename in files:
            path = os.path.join(INPUT_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    order_data = extract_all_data(data)
                    current_results.append(order_data)
            except Exception as e:
                print(f"[!] Ошибка парсинга {filename}: {e}")

        changes = notifier.check_for_changes(current_results)
        if changes:
            notifier.send_alerts(changes)
        else:
            print("[*] Изменений нет.")

        try:
            shutil.rmtree(INPUT_DIR)
            os.makedirs(INPUT_DIR)
            print("[+] Папка debug_json очищена.")
        except Exception as e:
            print(f"[-] Не удалось очистить папку: {e}")
    else:
        print("[-] Новых данных не собрано. Проверь куки.")


async def main():
    while True:
        await run_iteration()
        wait_min = random.randint(CHECK_INTERVAL[0], CHECK_INTERVAL[1])
        print(f"[*] Ждем {wait_min} мин. до следующей проверки...")
        await asyncio.sleep(wait_min * 60)


if __name__ == "__main__":
    asyncio.run(main())