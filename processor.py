import json
import re


def extract_all_data(data):
    def flatten_to_dict(y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x: flatten(x[a], name + a + '.')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '.')
                    i += 1
            else:
                if isinstance(x, str) and (x.startswith('{') or x.startswith('[')):
                    try:
                        sub_json = json.loads(x)
                        flatten(sub_json, name)
                    except:
                        out[name[:-1]] = x
                else:
                    out[name[:-1]] = x

        flatten(y)
        return out

    flat_data = flatten_to_dict(data)

    res = {
        "ID Заказа": "Н/Д",
        "Статус": "ОПРЕДЕЛЯЕТСЯ",
        "Состав": [],
        "Стоимость": "Не найдена",
        "Адрес": "Не найден",
        "QR-код": "Нет QR"
    }

    def clean(t):
        if not t: return ""
        t = re.sub('<[^<]+?>', '', str(t))
        return t.replace('\u2009', ' ').replace('\u202f', ' ').replace('\xa0', ' ').strip()

    shipment_map = {}

    # --- НОВЫЕ ФЛАГИ ДЛЯ ТОЧНОГО СТАТУСА ---
    is_ready_by_widget = False  # Флаг: найден ли виджет выдачи (QR)
    found_main_status = ""  # Сюда сохраним заголовок, если он "сильный"

    for key, value in flat_data.items():
        val_str = str(value)
        k_low = key.lower()

        # 1. ПРОВЕРКА НА ГОТОВНОСТЬ (receiptCode — это системное имя виджета выдачи)
        if "receiptcode" in k_low or "qr-code" in val_str:
            is_ready_by_widget = True

        # 2. ID ЗАКАЗА
        if "order" in k_low and "-" in val_str:
            oid = re.search(r'(\d{10}-\d{4})', val_str)
            if oid: res["ID Заказа"] = oid.group(1)

        # 3. СТОИМОСТЬ
        if "₽" in val_str and any(x in k_low for x in ["price", "total", "amount"]):
            res["Стоимость"] = clean(val_str)

        # 4. QR-КОД
        if "qr-code" in val_str and val_str.startswith('http'):
            res["QR-код"] = val_str

        # 5. АДРЕС
        if any(word in val_str for word in ["Смолячкова", "ул.", "проспект"]) and len(val_str) > 10:
            if not any(x in val_str for x in ["{", "http", "main"]):
                res["Адрес"] = clean(val_str)

        # 6. ТОВАРЫ И ПОЗИЦИОННЫЕ СТАТУСЫ
        ship_id = re.search(r'shipmentWidget-[\d\w-]+', key)
        if ship_id:
            s_id = ship_id.group(0)
            if s_id not in shipment_map:
                shipment_map[s_id] = {"status": "В ПУТИ", "items": []}

            if ".header." in key and ".text" in key:
                status_cand = clean(val_str).upper()
                # Если в тексте есть "ЗАБИРАТЬ", помечаем заказ как готовый
                if "ЗАБИРАТЬ" in status_cand or "ГОТОВ" in status_cand:
                    is_ready_by_widget = True

                if any(s in status_cand for s in ["ПУТИ", "ЗАБИРАТЬ", "ДОСТАВЛЕНО", "ОЖИДАЕТ", "АПРЕЛЯ"]):
                    shipment_map[s_id]["status"] = status_cand.replace("ИЗ ПУНКТА ВЫДАЧИ ", "")

            if ".title.name.text" in key:
                item_name = clean(val_str)
                if len(item_name) > 10 and "textPrimary" not in item_name:
                    shipment_map[s_id]["items"].append(item_name)

    # --- СБОРКА И ФИНАЛЬНАЯ ЛОГИКА СТАТУСА ---
    final_items = []
    for s_id, s_data in shipment_map.items():
        st = s_data["status"]
        for it in s_data["items"]:
            final_items.append(f"{it} — [{st}]")

    res["Состав"] = list(dict.fromkeys(final_items)) if final_items else ["Товары не найдены"]

    # ЛОГИКА ОПРЕДЕЛЕНИЯ ГЛАВНОГО СТАТУСА:
    if is_ready_by_widget:
        # Если нашли receiptCode или слово "забирать" — игнорим даты, пишем ГОТОВО
        res["Статус"] = "МОЖНО ЗАБИРАТЬ"
    elif shipment_map:
        # Если не готовы, берем статус первого отправления
        res["Статус"] = list(shipment_map.values())[0]["status"]

    return res