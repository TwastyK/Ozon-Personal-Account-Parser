import asyncio
import os
import json
import re

from playwright.async_api import async_playwright

COOKIE_PATH = os.path.join(os.getcwd(), "user_cookie")
DEBUG_DIR = os.path.join(os.getcwd(), "debug_json")

captured_ids = set()


async def handle_response(response):
    """Перехватчик сетевых ответов"""
    if "application/json" in response.headers.get("content-type", ""):
        url = response.url
        if "orderlist" in url or "orderdetails" in url:
            try:
                text = await response.text()
                data = json.loads(text)

                prefix = "list" if "orderlist" in url else "details"
                ts = int(asyncio.get_event_loop().time())
                filename = os.path.join(DEBUG_DIR, f"{prefix}_{ts}.json")

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                if "orderlist" in url:
                    found = re.findall(r'\d{10}-\d{4}', text)
                    for oid in found:
                        captured_ids.add(oid)
            except:
                pass


async def collect_data():
    """Главная функция, которую вызывает main.py"""
    global captured_ids
    captured_ids.clear()

    if not os.path.exists(DEBUG_DIR):
        os.makedirs(DEBUG_DIR)

    async with async_playwright() as p:
        if not os.path.exists(COOKIE_PATH):
            print(f"[-] Ошибка: Куки не найдены в {COOKIE_PATH}")
            return

        context = await p.chromium.launch_persistent_context(
            user_data_dir=COOKIE_PATH,
            headless=False,  # Поставить True, если хочешь чтобы работало в фоне
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )

        page = context.pages[0] if context.pages else await context.new_page()
        page.on("response", handle_response)

        print("[+] Collector: Загрузка Ozon...")
        await page.goto("https://www.ozon.ru/my/orderlist", wait_until="domcontentloaded")

        # --- АКТИВНЫЙ ВЗЛОМ КЭША (Fetch API) ---
        # Быстрый скролл вниз и возврат вверх, чтобы триггернуть ленивую загрузку
        await page.mouse.wheel(0, 3000)
        await asyncio.sleep(2)
        await page.mouse.wheel(0, -3000)
        # 1. Запрашиваем список заказов
        print("[*] Collector: Force Fetch списка заказов...")
        await page.evaluate("""
            fetch('/api/entrypoint-api.bx/page/json/v2?url=%2Fmy%2Forderlist%3FselectedTab%3Dactive');
        """)

        # Ждем появления ID в captured_ids
        for _ in range(8):
            if captured_ids: break
            await asyncio.sleep(1)

        if not captured_ids:
            print("[!] Collector: ID не найдены в API. Пробую скролл...")
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(3)

        print(f"[+] Collector: Найдено ID для проверки: {len(captured_ids)}")

        # 2. Запрашиваем детали для каждого ID (чтобы processor.py их увидел)
        for oid in list(captured_ids):
            print(f"[*] Collector: Fetch деталей для {oid}...")
            await page.evaluate(f"""
                fetch('/api/entrypoint-api.bx/page/json/v2?url=%2Fmy%2Forderdetails%3Forder%3D{oid}');
            """)
            await asyncio.sleep(2)  # Небольшая пауза, чтобы не поймать бан

        print("[+] Collector: Сбор завершен.")
        await context.close()


# Если запустить файл напрямую — он тоже сработает
if __name__ == "__main__":
    asyncio.run(collect_data())