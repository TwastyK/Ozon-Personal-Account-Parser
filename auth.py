import asyncio
from playwright.async_api import async_playwright


async def open_ozon_with_profile():
    async with async_playwright() as p:
        # Путь к твоей папке с профилем
        user_data_dir = r"F:\Cookie\user_cookie"

        # Запускаем браузер с твоими данными
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,  # Обязательно False, чтобы видеть окно
            # Убираем флаг автоматизации, чтобы Ozon меньше ругался
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # Берем уже открытую страницу или создаем новую
        page = context.pages[0] if context.pages else await context.new_page()

        print("[*] Переходим на Ozon...")
        try:
            # networkidle подождет, пока запросы утихнут
            await page.goto("https://www.ozon.ru/my/orderlist", wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"[-] Загрузка заняла много времени, но проверяй окно браузера: {e}")

        print("[!] Проверь окно браузера. Если залогинило — всё ок.")

        # Этот блок держит браузер открытым, пока ты не нажмешь Ctrl+C
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(open_ozon_with_profile())