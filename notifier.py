import json
import os

STATE_FILE = "last_state.json"


def load_last_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_current_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


def check_for_changes(current_orders):
    last_state = load_last_state()
    new_state = {}
    changes_detected = []

    for order in current_orders:
        oid = order.get("ID Заказа")
        new_status = order.get("Статус")

        if not oid or oid == "Н/Д":
            continue

        new_state[oid] = order

        if oid in last_state:
            old_status = last_state[oid].get("Статус")
            if old_status != new_status:
                changes_detected.append({
                    "id": oid,
                    "old": old_status,
                    "new": new_status,
                    "items": order.get("Состав")
                })
        else:
            changes_detected.append({
                "id": oid,
                "old": "НОВЫЙ",
                "new": new_status,
                "items": order.get("Состав")
            })

    save_current_state(new_state)
    return changes_detected


def send_alerts(changes):
    for change in changes:
        print(f"\n🔔 [ИЗМЕНЕНИЕ] Заказ {change['id']}")
        print(f"   Было: {change['old']} -> Стало: {change['new']}")
        print(f"   Состав: {change['items'][:100]}...")