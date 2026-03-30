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
                # ШАГ 1: РАСКРЫВАЕМ МАТРЕШКУ (как в твоем TXT)
                if isinstance(x, str) and (x.startswith('{') or x.startswith('[')):
                    try:
                        sub_json = json.loads(x)
                        flatten(sub_json, name)  # Уходим вглубь
                    except:
                        out[name[:-1]] = x
                else:
                    out[name[:-1]] = x

        flatten(y)
        return out

    # Сначала получаем ПОЛНУЮ плоскую карту всех данных
    flat_data = flatten_to_dict(data)

    res = {
        "ID Заказа": "Н/Д",
        "Статус": "ОПРЕДЕЛЯЕТСЯ",
        "Состав": [],
        "Стоимость": "Не найдена",
        "Адрес": "Не найден",
        "QR-код": "Нет QR",
        "UF_CRM_OZON_SHIPMENT_DATE": "Н/Д",
        "UF_CRM_OZON_BARCODE": "Н/Д",
        "UF_CRM_OZON_IS": True,
        "UF_CRM_OZON_DELIVERY": "Ozon",
        "UF_CRM_OZON_POSTING_NUMBER": "Н/Д",
        "UF_CRM_OZON_TRACK_NUMBER": "Н/Д",
        "UF_CRM_OZON_STATUS": "Н/Д",
        "UF_CRM_ROZORDERNUMBER": "Н/Д"
    }

    def clean(t):
        if not t: return ""
        t = re.sub('<[^<]+?>', '', str(t))
        # Фильтр технических заголовков Ozon, которые не являются данными
        bad_words = ["textPrimary", "ozTextPrimary", "ozParent", "main", "horizontal", "vertical"]
        if any(w == t for w in bad_words): return ""
        return t.replace('\u2009', ' ').replace('\u202f', ' ').replace('\xa0', ' ').strip()

    shipment_map = {}
    is_ready_by_widget = False

    # ШАГ 2: ИДЕМ ПО КАРТЕ PATH (когда матрешка уже раскрыта)
    for key, value in flat_data.items():
        val_str = str(value)

        # 1. СТОИМОСТЬ (Твой путь: orderDoneTotal...total.right.price.text)
        if "orderDoneTotal" in key and "total.right.price.text" in key:
            val_cleaned = clean(val_str)
            if val_cleaned: res["Стоимость"] = val_cleaned

        # 2. БАРКОД / КОД ВЫДАЧИ (Твой путь: receiptCode...code.text)
        if "receiptCode" in key and "code.text" in key:
            res["UF_CRM_OZON_BARCODE"] = val_str
            res["UF_CRM_OZON_TRACK_NUMBER"] = val_str  # Для Озона это по сути трек

        # 3. ДАТА ДОСТАВКИ (Твой путь: shipmentWidget...header...text)
        if "shipmentWidget" in key and "header" in key and "textIcon.text.text" in key:
            val_cleaned = clean(val_str)
            if val_cleaned: res["UF_CRM_OZON_SHIPMENT_DATE"] = val_cleaned

        # 4. НОМЕР ЗАКАЗА / ОТПРАВЛЕНИЯ (Чистим от ссылок)
        if re.search(r'\d{10}-\d{4}', val_str):
            match = re.search(r'(\d{10}-\d{4})', val_str)
            if match:
                oid = match.group(1)
                res["ID Заказа"] = oid
                res["UF_CRM_OZON_POSTING_NUMBER"] = oid
                res["UF_CRM_ROZORDERNUMBER"] = oid

        # 5. АДРЕС И QR (Старая добрая логика)
        if any(word in val_str for word in ["Смолячкова", "ул.", "проспект"]) and len(val_str) > 10:
            if not any(x in val_str for x in ["{", "http"]):
                res["Адрес"] = clean(val_str)

        if "qr-code" in val_str and val_str.startswith('http'):
            res["QR-код"] = val_str

        # 6. СБОР СОСТАВА ТОВАРОВ
        if "shipmentWidget" in key:
            ship_id_match = re.search(r'shipmentWidget-[\d\w-]+', key)
            if ship_id_match:
                s_id = ship_id_match.group(0)
                if s_id not in shipment_map:
                    shipment_map[s_id] = {"status": "В ПУТИ", "items": []}

                if ".header." in key and ".text" in key:
                    status_cand = clean(val_str).upper()
                    if "ЗАБИРАТЬ" in status_cand or "ГОТОВ" in status_cand:
                        is_ready_by_widget = True
                    if status_cand: shipment_map[s_id]["status"] = status_cand

                if ".title.name.text" in key:
                    item_name = clean(val_str)
                    if len(item_name) > 10:
                        shipment_map[s_id]["items"].append(item_name)

    # Финальная сборка
    final_items = []
    for s_id, s_data in shipment_map.items():
        st = s_data["status"]
        for it in s_data["items"]:
            final_items.append(f"{it} — [{st}]")
    res["Состав"] = list(dict.fromkeys(final_items))

    if is_ready_by_widget:
        res["Статус"] = "МОЖНО ЗАБИРАТЬ"
    elif shipment_map:
        res["Статус"] = list(shipment_map.values())[0]["status"]

    res["UF_CRM_OZON_STATUS"] = res["Статус"]

    return res