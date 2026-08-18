import asyncio
import json
import os
import re
from datetime import datetime

from playwright.async_api import async_playwright

from app.stats import stats, save_stats
from app.notifier import notify


ACCOUNTS_DIR = "data/accounts"
ORDERS_DIR = "data/orders"
REMINDERS_FILE = "data/review_reminders.json"

CHECK_INTERVAL = 30
REVIEW_REMINDER_DELAY = 2 * 60 * 60


FUNPAY_STATS_FILE = "data/funpay_stats.json"


def update_funpay_stats(user_id, order):

    os.makedirs(
        "data",
        exist_ok=True
    )

    if os.path.exists(FUNPAY_STATS_FILE):

        try:
            with open(
                FUNPAY_STATS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

        except:
            data = {}

    else:
        data = {}


    user = data.setdefault(
        str(user_id),
        {
            "orders_total": 0,
            "orders_done": 0,
            "turnover_total": 0,
            "buyers": 0
        }
    )


    user["orders_total"] += 1
    user["orders_done"] += 1


    price = re.findall(
        r"\d+",
        order.get("price", "")
    )

    if price:
        user["turnover_total"] += int(price[0])


    if order.get("buyer") != "Не найден":
        user["buyers"] += 1


    with open(
        FUNPAY_STATS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def get_accounts():
    accounts = []

    if not os.path.exists(ACCOUNTS_DIR):
        return accounts

    for filename in os.listdir(ACCOUNTS_DIR):

        if not filename.endswith("_funpay.json"):
            continue

        try:
            user_id = int(
                filename.replace("_funpay.json", "")
            )
        except ValueError:
            continue

        accounts.append({
            "user_id": user_id,
            "session": os.path.join(
                ACCOUNTS_DIR,
                filename
            )
        })

    return accounts


def get_orders_file(user_id):
    return os.path.join(
        ORDERS_DIR,
        f"{user_id}.json"
    )


def load_orders(user_id):
    path = get_orders_file(user_id)

    if not os.path.exists(path):
        return []

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:
        print(
            f"[{user_id}] Ошибка загрузки заказов:",
            repr(e)
        )

    return []


def save_orders(user_id, orders):
    os.makedirs(
        ORDERS_DIR,
        exist_ok=True
    )

    path = get_orders_file(user_id)

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            orders,
            f,
            indent=4,
            ensure_ascii=False
        )


def get_order_ids(text):
    return list(
        dict.fromkeys(
            re.findall(
                r"#[A-Z0-9]+",
                text
            )
        )
    )


def parse_order(text, order_id):

    data = {
        "order": order_id,
        "buyer": "Не найден",
        "product": "Не найден",
        "price": "Не найдена"
    }

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    for index, line in enumerate(lines):

        if order_id not in line:
            continue

        around = lines[index:index + 15]

        for item in around:

            low = item.lower()

            if "₽" in item:
                data["price"] = item
                continue

            if (
                "roblox" in low
                or "робукс" in low
                or "робуксов" in low
            ):
                data["product"] = item
                continue

            if (
                item != order_id
                and item != data["product"]
                and "₽" not in item
                and len(item) < 30
                and "roblox" not in low
                and "робукс" not in low
                and "робуксов" not in low
            ):

                if data["buyer"] == "Не найден":
                    data["buyer"] = item

        break

    return data


def load_reminders():

    if not os.path.exists(REMINDERS_FILE):
        return {}

    try:

        with open(
            REMINDERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception as e:

        print(
            "Ошибка загрузки напоминаний:",
            repr(e)
        )

    return {}


def save_reminders(data):

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        REMINDERS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def create_review_reminder(
    user_id,
    username,
    order_id
):

    reminders = load_reminders()

    key = f"{user_id}:{username}"

    reminders[key] = {
        "user_id": user_id,
        "username": username,
        "order": order_id,
        "time": __import__("datetime")
        .datetime.now()
        .strftime("%Y-%m-%d %H:%M:%S")
    }

    save_reminders(reminders)

    print(
        f"[{user_id}] ⭐ Напоминание об отзыве создано:",
        username
    )


async def monitor_one_account(account):

    user_id = account["user_id"]
    session_file = account["session"]

    print(
        f"🟢 Запуск мониторинга {user_id}"
    )

    saved_orders = load_orders(user_id)

    first_run = not bool(saved_orders)

    async with async_playwright() as p:

        browser = None

        try:

            browser = await p.chromium.launch(
                headless=True
            )

            context = await browser.new_context(
                storage_state=session_file
            )

            page = await context.new_page()

            while True:

                try:

                    await page.goto(
                        "https://funpay.com/orders/trade",
                        wait_until="domcontentloaded"
                    )

                    await page.wait_for_timeout(
                        2500
                    )

                    body = await page.locator(
                        "body"
                    ).inner_text()

                    current_ids = get_order_ids(
                        body
                    )

                    stats["orders"] = len(
                        current_ids
                    )

                    print(
                        f"[{user_id}] "
                        f"Заказов найдено: "
                        f"{len(current_ids)}"
                    )

                    if first_run:

                        saved_orders = (
                            current_ids.copy()
                        )

                        save_orders(
                            user_id,
                            saved_orders
                        )

                        first_run = False

                        print(
                            f"[{user_id}] "
                            "🟡 Первый запуск — "
                            "база заказов создана"
                        )

                    else:

                        new_orders = [
                            order_id
                            for order_id in current_ids
                            if order_id not in saved_orders
                        ]

                        for order_id in new_orders:

                            print(
                                f"[{user_id}] "
                                "🟢 НОВЫЙ ЗАКАЗ:",
                                order_id
                            )

                            order = parse_order(
                                body,
                                order_id
                            )

                            update_funpay_stats(
                                user_id,
                                order
                            )

                            message = (
                                "🛒 Новый заказ FunPay\n\n"
                                f"🏷 Заказ: "
                                f"{order['order']}\n"
                                f"📦 Товар: "
                                f"{order['product']}\n"
                                f"👤 Покупатель: "
                                f"{order['buyer']}\n"
                                f"💰 Цена: "
                                f"{order['price']}\n\n"
                                "🟢 Market Notify"
                            )

                            try:

                                await notify(
                                    user_id,
                                    message
                                )

                                stats[
                                    "new_orders"
                                ] += 1

                                save_stats()

                                print(
                                    f"[{user_id}] "
                                    "🔔 Уведомление "
                                    "отправлено"
                                )

                            except Exception as e:

                                print(
                                    f"[{user_id}] "
                                    "❌ Ошибка уведомления:",
                                    repr(e)
                                )

                            # Если покупатель найден —
                            # создаём напоминание об отзыве.
                            if (
                                order["buyer"] != "Не найден"
                            ):

                                create_review_reminder(
                                    user_id,
                                    order["buyer"],
                                    order_id
                                )

                        saved_orders = (
                            current_ids.copy()
                        )

                        save_orders(
                            user_id,
                            saved_orders
                        )

                except Exception as e:

                    print(
                        f"[{user_id}] "
                        "⚠️ Ошибка проверки:",
                        repr(e)
                    )

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

        finally:

            if browser:

                try:
                    await browser.close()
                except:
                    pass


async def monitor_orders():

    print(
        "🔥 FUNPAY MONITOR ЗАПУЩЕН"
    )

    accounts = get_accounts()

    if not accounts:

        print(
            "❌ Подключённых FunPay аккаунтов нет"
        )

        while True:
            await asyncio.sleep(60)

    tasks = []

    for account in accounts:

        print(
            account
        )

        tasks.append(
            asyncio.create_task(
                monitor_one_account(
                    account
                )
            )
        )

    await asyncio.gather(
        *tasks
    )