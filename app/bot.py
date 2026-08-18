import json
import os
import asyncio
import random
import time

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import BOT_TOKEN
from app.funpay import monitor_orders, get_accounts
from app.connect_funpay import connect_account
from app.funpay_chat import monitor_chat


from app.bot_instance import bot

dp = Dispatcher()

class PromoState(StatesGroup):
    code = State()
    bonus = State()
    activations = State()


class PointsState(StatesGroup):

    add_user = State()
    add_amount = State()

    remove_user = State()
    remove_amount = State()


PROMO_FILE = "data/promos.json"
waiting_promo = set()
waiting_delete_promo = set()
broadcast_wait = set()
waiting_pro = {}
waiting_shop_add = set()
waiting_shop_delete = set()
waiting_add_points = set()
waiting_remove_points = set()

bot_messages = {}



from app.storage import order_messages

funpay_task = None
chat_task = None



# =========================
# Создание папок
# =========================

def init_data():

    os.makedirs(
        "data",
        exist_ok=True
    )

    os.makedirs(
        "data/stats",
        exist_ok=True
    )

    os.makedirs(
        "data/points",
        exist_ok=True
    )


init_data()

# =========================
# Файлы
# =========================

def is_admin(user_id):

    try:

        with open(
            "data/admin.txt",
            "r",
            encoding="utf-8"
        ) as file:

            admins = file.read().splitlines()

        return str(user_id) in admins

    except:

        return False



def get_plan(user_id):

    try:

        with open(
            "data/plans.json",
            "r",
            encoding="utf-8"
        ) as file:

            plans = json.load(file)


        return plans.get(
            str(user_id),
            "free"
        )


    except:

        return "free"



def save_json(path, data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )



def load_json(path, default):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except:

        return default


def load_promos():
    try:
        with open(
            "data/promos.json",
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except:
        return {}


def save_promos(data):
    with open(
        "data/promos.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )



if os.path.exists("data/bot_messages.json"):

    bot_messages = load_json(
        "data/bot_messages.json",
        {}
    )


POINTS_DIR = "data/points"


def get_points(user_id):

    path = f"{POINTS_DIR}/{user_id}.json"

    data = load_json(
        path,
        {
            "balance": 0,
            "last_wheel": 0
        }
    )

    return data


def save_points(user_id, data):

    path = f"{POINTS_DIR}/{user_id}.json"

    save_json(
        path,
        data
    )




def add_points(user_id, amount):

    data = load_json(
        POINTS_FILE,
        {}
    )

    uid = str(user_id)

    if uid not in data:

        data[uid] = {
            "balance": 0,
            "last_spin": None
        }


    data[uid]["balance"] += amount


    save_json(
        POINTS_FILE,
        data
    )


user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📱 Мои аккаунты"),
            KeyboardButton(text="📊 Статистика")
        ],
        [
            KeyboardButton(text="⭐ Premium"),
            KeyboardButton(text="🎡 Колесо")
        ],
        [
            KeyboardButton(text="🛒 Магазин"),
            KeyboardButton(text="🎁 Промокоды")
        ],
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="ℹ️ Помощь")
        ],
        [
            KeyboardButton(text="🛒 Наш FunPay")
        ]
    ],
    resize_keyboard=True
)


admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📦 Заказы"),
            KeyboardButton(text="📊 Статистика")
        ],
        [
            KeyboardButton(text="👥 Пользователи"),
            KeyboardButton(text="📱 Аккаунты")
        ],
        [
            KeyboardButton(text="👑 Управление Premium"),
            KeyboardButton(text="💰 Баланс")
        ],
        [
            KeyboardButton(text="🛒 Магазин"),
            KeyboardButton(text="🎁 Промокоды")
        ],
        [
            KeyboardButton(text="📢 Рассылка")
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
            KeyboardButton(text="ℹ️ Помощь")
        ]
    ],
    resize_keyboard=True
)



users_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="📋 Список")
        ],

        [
            KeyboardButton(text="📊 Всего")
        ],

        [
            KeyboardButton(text="📱 Подключено FunPay")
        ],

        [
            KeyboardButton(text="🎮 Подключено PlayerOK")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)

premium_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="➕ Выдать Premium")
        ],

        [
            KeyboardButton(text="➖ Забрать Premium")
        ],

        [
            KeyboardButton(text="📋 Список Premium")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)


points_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="⭐ Выдать баланс")
        ],

        [
            KeyboardButton(text="➖ Забрать баланс")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)



broadcast_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)


promo_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Создать промокод")
        ],
        [
            KeyboardButton(text="📋 Список промокодов"),
            KeyboardButton(text="🗑 Удалить промокод")
        ],
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)



back_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)


promo_create_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ Отмена"),
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)


wheel_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="🎡 Крутить колесо")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)



settings_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="⚡ 30 секунд"),
            KeyboardButton(text="⏱ 60 секунд")
        ],

        [
            KeyboardButton(text="🐢 120 секунд")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)



# =========================
# Удаление сообщений
# =========================

async def delete_last_menu(user_id):

    if user_id not in last_menu_messages:
        return


    try:

        await bot.delete_message(
            chat_id=user_id,
            message_id=last_menu_messages[user_id]
        )

    except:

        pass


    del last_menu_messages[user_id]



async def delete_user_message(message: Message):

    try:

        await message.delete()

    except:

        pass

async def send_menu(user_id, text, reply_markup):

    uid = str(user_id)

    if uid in bot_messages:

        try:
            await bot.delete_message(
                chat_id=user_id,
                message_id=bot_messages[uid]
            )
        except:
            pass

    msg = await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=reply_markup
    )

    bot_messages[uid] = msg.message_id

    save_json(
        "data/bot_messages.json",
        bot_messages
    )



async def get_start_text(user_id):

    data = get_points(
        user_id
    )


    return (
        "👋 Добро пожаловать в Market Notify!\n\n"

        "🤖 Ваш помощник для автоматизации продаж.\n\n"

        "🛒 FunPay мониторинг\n"
        "📦 Уведомления о заказах\n"
        "📊 Статистика продаж\n"
        "🎡 Бонусы и магазин\n\n"

        "⚡ Быстро. Удобно. Автоматически.\n\n"

        "Выберите нужный раздел ниже 👇"
    )




async def send_answer(user_id, text, reply_markup=None):

    uid = str(user_id)

    if reply_markup is None:
        if is_admin(user_id):
            reply_markup = admin_menu
        else:
            reply_markup = user_menu

    if uid in bot_messages:

        try:
            await bot.delete_message(
                chat_id=user_id,
                message_id=bot_messages[uid]
            )
        except:
            pass

    msg = await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=reply_markup
    )

    bot_messages[uid] = msg.message_id

    save_json(
        "data/bot_messages.json",
        bot_messages
    )

# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):

    from datetime import datetime

    profiles = load_json(
        "data/user_profiles.json",
        {}
    )

    uid = str(message.from_user.id)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")


    if uid not in profiles:

        profiles[uid] = {
            "registered": now,
            "last_login": now
        }

    else:

        profiles[uid]["last_login"] = now


    save_json(
        "data/user_profiles.json",
        profiles
    )


    await delete_user_message(
        message
    )

    user_id = message.from_user.id


    # очищаем старые режимы

    if user_id in waiting_promo:

        waiting_promo.remove(
            user_id
        )


    if user_id in broadcast_wait:

        broadcast_wait.remove(
            user_id
        )


    # удаляем старое меню после перезапуска

    if str(user_id) in bot_messages:

        try:

            await bot.delete_message(
                chat_id=user_id,
                message_id=bot_messages[str(user_id)]
            )

        except Exception as e:

            print(
                "Ошибка удаления старого меню:",
                e
            )

        del bot_messages[str(user_id)]

        save_json(
            "data/bot_messages.json",
            bot_messages
        )



    # Удаляем уведомление о новом заказе
    if user_id in order_messages:

        try:

            await bot.delete_message(
                chat_id=user_id,
                message_id=order_messages[user_id]
            )

        except Exception as e:

            print(
                "Ошибка удаления заказа:",
                e
            )

        del order_messages[user_id]


    users = load_json(
        "data/users.json",
        []
    )


    if user_id not in users:

        users.append(
            user_id
        )

        save_json(
            "data/users.json",
            users
        )

    if is_admin(user_id):

        await send_menu(
            user_id,

            (
                "👑 Market Notify\n\n"

                "Добро пожаловать, администратор.\n\n"

                "📦 Мониторинг заказов\n"
                "💬 Мониторинг чатов\n"
                "📊 Статистика\n"
                "⚙️ Управление ботом\n\n"

                "Выберите действие ниже 👇"
            ),

            admin_menu
        )

    else:

        await send_menu(
            user_id,

            await get_start_text(
                user_id
            ),

            user_menu
        )

# =========================
# Статус
# =========================

@dp.message(
    lambda m: m.text == "📊 Статус"
)
async def status(message: Message):


    await delete_user_message(
        message
    )

    user_id = message.from_user.id


    await send_menu(
        user_id,

        (
            "📊 Market Notify\n\n"

            "🟢 Статус: работает\n\n"

            "🤖 Telegram\n"
            "🟢 Онлайн\n\n"

            "🛒 Market\n"
            "🟢 Мониторинг активен\n\n"

            "⏱ Проверка заказов:\n"
            "каждые 30 секунд"
        ),

        back_menu
    )


@dp.message(
    lambda m: m.text == "🎡 Колесо"
)
async def wheel(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    data = get_points(
        user_id
    )

    await send_menu(
        user_id,

        "🎡 Колесо удачи\n\n"
        f"💰 Ваш баланс: {data['balance']} ₽\n\n"
        "Нажмите кнопку ниже и попробуйте удачу 🎁",

        wheel_menu
    )


@dp.message(
    lambda m: m.text == "🎡 Крутить колесо"
)
async def spin_wheel(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    data = get_points(
        user_id
    )

    now = time.time()


    if data.get("last_spin"):

        passed = now - data["last_spin"]

        if passed < 3600:

            minutes = int(
                (3600 - passed) / 60
            )

            await send_menu(
                user_id,

                "⏳ Колесо уже использовано.\n\n"
                f"Попробуйте через {minutes} минут.",

                wheel_menu
            )

            return


    prizes = [
        0,
        5,
        10,
        25,
        50
    ]


    reward = random.choice(
        prizes
    )


    # сохраняем время кручения в профиль пользователя
    data["last_spin"] = now

    save_points(
        user_id,
        data
    )


    if reward > 0:

        add_points(
            user_id,
            reward
        )


        text = (
            "🎉 Поздравляем!\n\n"
            f"Вы выиграли 💰 {reward} ₽!\n\n"
            "Деньги добавлены на ваш баланс."
        )


    else:

        text = (
            "😢 В этот раз ничего не выпало.\n\n"
            "Попробуйте ещё раз позже!"
        )


    data = get_points(
        user_id
    )


    await send_menu(
        user_id,

        text +
        "\n\n💰 Баланс: "
        f"{data['balance']} ₽",

        wheel_menu
    )


# =========================
# Магазин
# =========================

@dp.message(lambda m: m.text == "🛒 Магазин")
async def shop(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    if is_admin(user_id):

        await send_menu(
            user_id,

            "🛒 Управление магазином\n\n"
            "Выберите действие:",

            shop_admin_menu
        )

        return


    products = load_json(
        "data/shop.json",
        []
    )

    if not products:

        await send_menu(
            user_id,
            "🛒 Магазин пуст.",
            user_menu
        )

        return

    text = "🛒 Магазин\n\n"

    for item in products:

        text += (
            f"{item['name']}\n"
            f"💰 Цена: {item['price']} ₽\n"
            f"📝 {item['description']}\n\n"
        )

    buttons = []

    for item in products:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item['name']} — 💰 {item['price']} ₽",
                    callback_data=f"buy_{item['id']}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="shop_back"
            )
        ]
    )

    shop_kb = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    if str(user_id) in bot_messages:
        try:
            await bot.delete_message(
                chat_id=user_id,
                message_id=bot_messages[str(user_id)]
            )
        except:
            pass

    msg = await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=shop_kb
    )

    bot_messages[str(user_id)] = msg.message_id

    save_json(
        "data/bot_messages.json",
        bot_messages
    )


# =========================
# Покупка товара
# =========================

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(callback):

    user_id = callback.from_user.id

    product_id = int(
        callback.data.split("_")[1]
    )

    products = load_json(
        "data/shop.json",
        []
    )

    product = None

    for item in products:

        if item["id"] == product_id:

            product = item
            break

    if not product:

        await callback.answer("❌ Товар не найден")

        return

    data = get_points(user_id)

    price = product["price"]

    if data["balance"] < price:

        await callback.answer("❌ Недостаточно рублей")

        return

    data["balance"] -= price

    save_points(user_id, data)

    await callback.message.edit_text(
        "✅ Покупка успешна!\n\n"
        f"{product['name']}\n\n"
        f"💰 Потрачено: {price} ₽\n"
        f"💰 Осталось: {data['balance']} ₽"
    )

    await callback.answer("Покупка выполнена")


# =========================
# Назад из магазина
# =========================

@dp.callback_query(lambda c: c.data == "shop_back")
async def shop_back(callback):

    user_id = callback.from_user.id

    try:
        await callback.message.delete()
    except:
        pass

    bot_messages.pop(str(user_id), None)

    save_json(
        "data/bot_messages.json",
        bot_messages
    )

    await send_menu(
        user_id,
        await get_start_text(user_id),
        admin_menu if is_admin(user_id) else user_menu
    )

    await callback.answer()

# =========================
# Статистика
# =========================

@dp.message(
    lambda m: m.text == "📊 Статистика"
)
async def stats(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id


    if is_admin(user_id):

        users = load_json(
            "data/users.json",
            []
        )

        plans = load_json(
            "data/plans.json",
            {}
        )

        pro_count = 0

        for uid, plan in plans.items():

            if plan == "premium":
                pro_count += 1


        await send_menu(
            user_id,

            "📊 Админ статистика\n\n"
            f"👥 Пользователей: {len(users)}\n"
            f"⭐ Premium пользователей: {pro_count}",

            admin_menu
        )

        return


    data = load_json(
        f"data/stats/{user_id}.json",
        {
            "orders": 0,
            "money": 0,
            "buyers": 0
        }
    )


    accounts = load_json(
        f"data/accounts/{user_id}.json",
        []
    )


    await send_menu(
        user_id,

        "📊 Market Statistics\n\n"

        "━━━━━━━━━━━━━━\n\n"

        "🛒 Всего заказов:\n"
        f"{data.get('orders',0)}\n\n"

        "💰 Всего заработано:\n"
        f"{data.get('money',0)} ₽\n\n"

        "👥 Покупателей:\n"
        f"{data.get('buyers',0)}\n\n"

        "📱 Аккаунтов:\n"
        f"{len(accounts)}\n\n"

        "━━━━━━━━━━━━━━\n\n"

        "🟢 Market Notify",

        back_menu
    )


# =========================
# Тариф
# =========================

@dp.message(lambda m: m.text == "⭐ Premium")
async def plan(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id


    plan_data = get_plan(
        user_id
    )

    if isinstance(plan_data, dict):
        current = plan_data.get("plan")
        expires = plan_data.get("expires")
    else:
        current = plan_data
        expires = None


    if current == "admin":

        text = (
            "👑 Администратор\n\n"
            "✅ Без ограничений"
        )


    elif current == "premium":

        text = (
            "⭐ Premium\n\n"
            "✅ До 5 торговых аккаунтов"
            f"📅 Действует до: {expires}"
        )


    else:

        text = (
            "🆓 FREE\n\n"
            "✅ 1 торговый аккаунт"
        )


    await send_menu(
        user_id,
        text,
        back_menu
    )




# =========================
# Последний заказ
# =========================

@dp.message(
    lambda m: m.text == "📦 Последний заказ"
)
async def last_order(message: Message):

    await delete_user_message(
        message
    )


    if not is_admin(
        message.from_user.id
    ):
        return


    try:

        with open(
            "data/last_order.txt",
            "r",
            encoding="utf-8"
        ) as file:

            text = file.read()


        await send_answer(
            message.from_user.id,

            "📦 Последний заказ:\n\n"
            + text
        )


    except:

        await send_answer(
            message.from_user.id,
            "📭 Заказов нет"
        )



# =========================
# Пользователи
# =========================

@dp.message(lambda m: m.text == "👥 Пользователи")
async def users(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    await send_menu(
        user_id,
        "👥 Пользователи\n\nВыберите действие:",
        users_menu
    )


@dp.message(lambda m: m.text == "💰 Баланс")
async def points_panel(message: Message):

    if not is_admin(message.from_user.id):
        return

    await delete_user_message(message)

    await send_menu(
        message.from_user.id,
        "💰 Управление балансом\n\nВыберите действие:",
        points_menu
    )


@dp.message(lambda m: m.text == "📋 Список")
async def users_list(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    users = load_json(
        "data/users.json",
        []
    )

    text = "👥 Пользователи\n\n"

    for uid in users:
        text += f"👤 {uid}\n"

    await send_menu(
        user_id,
        text,
        users_menu
    )


@dp.message(lambda m: m.text == "📱 Подключено FunPay")
async def funpay_connected(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    if not is_admin(user_id):
        return


    count = 0

    path = "data/accounts"


    if os.path.exists(path):

        for file in os.listdir(path):

            if file.endswith("_funpay.json"):
                count += 1


    await send_menu(
        user_id,
        f"📱 Подключено FunPay\n\n"
        f"Всего аккаунтов: {count}",
        users_menu
    )


@dp.message(lambda m: m.text == "🎮 Подключено PlayerOK")
async def playerok_connected(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    if not is_admin(user_id):
        return


    count = 0

    path = "data/accounts"


    if os.path.exists(path):

        for file in os.listdir(path):

            if file.endswith("_playerok.json"):
                count += 1


    await send_menu(
        user_id,
        f"🎮 Подключено PlayerOK\n\n"
        f"Всего аккаунтов: {count}",
        users_menu
    )



@dp.message(lambda m: m.text == "📊 Всего")
async def users_count(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    users = load_json(
        "data/users.json",
        []
    )

    await send_menu(
        user_id,
        f"👥 Всего пользователей: {len(users)}",
        users_menu
    )


# =========================
# Premium
# =========================

@dp.message(lambda m: m.text == "➕ Выдать Premium")
async def give_pro(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    waiting_pro[user_id] = True

    await send_menu(
        user_id,
        "⭐ Выдача Premium\n\nВведите Telegram ID пользователя:",
        back_menu
    )


# =========================
# Забрать Premium
# =========================

@dp.message(lambda m: m.text == "➖ Забрать Premium")
async def remove_pro(message: Message):

    await delete_user_message(
        message
    )

    admin_id = message.from_user.id

    if not is_admin(admin_id):
        return


    waiting_pro[admin_id] = "remove"


    await send_menu(
        admin_id,

        "➖ Забрать Premium\n\n"
        "Введите Telegram ID пользователя:",

        back_menu
    )


@dp.message(
    lambda m: m.text and m.text.isdigit() and m.from_user.id in waiting_pro
)
async def pro_id_handler(message: Message):

    admin_id = message.from_user.id


    user_id = message.text.strip()


    await delete_user_message(
        message
    )


    if not is_admin(admin_id):
        return


    plans = load_json(
        "data/plans.json",
        {}
    )


    # Забрать Premium
    if waiting_pro[admin_id] == "remove":

        if user_id in plans:

            del plans[user_id]


            save_json(
                "data/plans.json",
                plans
            )


            await send_menu(
                admin_id,

                f"✅ У пользователя {user_id} Premium забран.",

                premium_menu
            )

        else:

            await send_menu(
                admin_id,

                "❌ У пользователя нет Premium.",

                premium_menu
            )


        del waiting_pro[admin_id]

        return



    # Выдать Premium

    expires = (
        datetime.now() + timedelta(days=30)
    ).strftime("%d.%m.%Y")


    plans[user_id] = {
        "plan": "premium",
        "expires": expires
    }



    save_json(
        "data/plans.json",
        plans
    )


    del waiting_pro[admin_id]


    await send_menu(
        admin_id,

        f"✅ Пользователь {user_id} получил Premium до {expires}.",

        premium_menu
    )

# =========================
# Настройки
# =========================

@dp.message(
    lambda m: m.text == "⚙️ Настройки"
)
async def settings(message: Message):

    await delete_user_message(
        message
    )


    await send_menu(
        message.from_user.id,
        "⚙️ Настройки\n\nВыберите интервал проверки:",
        settings_menu
    )



# =========================
# Назад
# =========================

@dp.message(
    lambda m: m.text == "⬅️ Назад"
)
async def back(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id

    if user_id in broadcast_wait:

        broadcast_wait.remove(
            user_id
        )


        await send_menu(
            user_id,

            "❌ Рассылка отменена.",

            admin_menu
        )

        return


    if is_admin(user_id):

        kb = admin_menu

    else:

        kb = user_menu


    await send_menu(
        user_id,

        await get_start_text(
            user_id
        ),

        kb
    )



# =========================
# Помощь
# =========================

@dp.message(
    lambda m: m.text == "ℹ️ Помощь"
)
async def help(message: Message):

    await delete_user_message(
        message
    )


    await send_menu(
        message.from_user.id,

        "ℹ️ Помощь\n\n"

        "🤖 Market Notify\n"
        "Автоматический помощник для продавцов цифровых товаров.\n\n"

        "Что умеет бот:\n\n"

        "✅ Отслеживание новых заказов\n"
        "✅ Уведомления о новых покупках\n"
        "✅ Автоматический ответ покупателям\n"
        "✅ Статистика продаж\n"
        "✅ Защита от повторных уведомлений\n"
        "✅ Работа с торговыми аккаунтами\n\n"

        "⚙️ Настройки:\n"
        "Вы можете изменить интервал проверки заказов.\n\n"

        "❓ Возникла проблема?\n"
        "Обратитесь в поддержку:\n\n"

        "👤 @seizux\n\n"

        "⚡ Версия бота: 1.0",

        back_menu
    )

# =========================
# Уведомления
# =========================

async def send_message(
        user_id,
        text
):


    await send_answer(
        user_id,
        text
    )

    print("bot_messages =", bot_messages)



# =========================
# Подключения
# =========================

accounts_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🛒 Подключить FunPay")
        ],

        [
            KeyboardButton(text="❌ Отключить FunPay")
        ],

        [
            KeyboardButton(text="🎮 Подключить PlayerOK (скоро)")
        ],
        [
            KeyboardButton(text="📋 Мои подключения")
        ],
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)


@dp.message(
    lambda m: m.text == "📱 Мои аккаунты"
)
async def accounts(message: Message):

    await delete_user_message(message)

    await send_menu(
        message.from_user.id,

        "📱 Управление аккаунтами\n\n"
        "Выберите действие:",

        accounts_menu
    )


waiting_funpay = set()


@dp.message(
    lambda m: m.text == "🛒 Подключить FunPay"
)
async def connect_funpay(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    waiting_funpay.add(user_id)

    await send_menu(
        user_id,

        "🛒 Подключение FunPay\n\n"
        "Отправьте ваш Golden Key.\n\n"
        "Его можно найти в настройках расширения FunPay.",

        back_menu
    )


@dp.message(
    lambda m: m.text == "❌ Отключить FunPay"
)
async def disconnect_funpay(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    path = f"data/accounts/{user_id}_funpay.json"

    if os.path.exists(path):

        os.remove(path)

        await send_menu(
            user_id,
            (
                "📱 Управление аккаунтами\n\n"
                "✅ FunPay отключён.\n\n"
                "Выберите действие:"
            ),
            accounts_menu
        )

    else:

        await send_menu(
            user_id,
            (
                "📱 Управление аккаунтами\n\n"
                "❌ FunPay не подключён.\n\n"
                "Выберите действие:"
            ),
            accounts_menu
        )

@dp.message(
    lambda m: m.text == "🎮 Подключить PlayerOK (скоро)"
)
async def playerok_soon(message: Message):

    await delete_user_message(message)

    msg = await message.answer(
        "🚧 Подключение PlayerOK\n\n"
        "Скоро будет доступно."
    )

    bot_messages[str(message.from_user.id)] = msg.message_id

    save_json(
        "data/bot_messages.json",
        bot_messages
    )


@dp.message(lambda m: m.text and "Промокод" in m.text and is_admin(m.from_user.id))
async def promo_panel(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    if is_admin(user_id):

        await send_menu(
            user_id,
            "🎁 Управление промокодами\n\nВыберите действие:",
            promo_menu
        )

    else:

        await send_menu(
            user_id,
            "🎁 Введите промокод:",
            back_menu
        )


@dp.message(lambda m: m.text and "Создать промокод" in m.text)
async def promo_create(message: Message, state: FSMContext):

    await delete_user_message(message)

    if not is_admin(message.from_user.id):
        return

    await state.clear()
    await state.set_state(PromoState.code)

    await send_menu(
        message.from_user.id,
        "🎁 Создание промокода\n\nВведите название промокода:",
        promo_create_menu
    )


@dp.message(lambda m: m.text == "🗑 Удалить промокод")
async def promo_delete_start(message: Message):

    if not is_admin(message.from_user.id):
        return

    await delete_user_message(message)

    waiting_delete_promo.add(message.from_user.id)

    await send_menu(
        message.from_user.id,
        "🗑 Введите код промокода для удаления:",
        back_menu
    )

@dp.message(lambda m: m.from_user.id in waiting_delete_promo)
async def promo_delete(message: Message):

    user_id = message.from_user.id

    await delete_user_message(message)

    code = message.text.strip().upper()

    promos = load_promos()

    if code not in promos:

        waiting_delete_promo.remove(user_id)

        await send_menu(
            user_id,
            "❌ Такой промокод не найден.",
            promo_menu
        )

        return


    del promos[code]

    save_promos(promos)

    waiting_delete_promo.remove(user_id)

    await send_menu(
        user_id,
        f"✅ Промокод {code} удалён.",
        promo_menu
    )



@dp.message(PromoState.code)
async def promo_code_step(message: Message, state: FSMContext):

    await delete_user_message(message)

    code = message.text.strip().upper()

    promos = load_promos()

    if code in promos:
        await send_menu(
            message.from_user.id,
            "❌ Такой промокод уже существует.\n\nВведите другой:",
            promo_create_menu
        )
        return

    await state.update_data(code=code)
    await state.set_state(PromoState.bonus)

    await send_menu(
        message.from_user.id,
        f"🎁 Код: {code}\n\n💎 Введите количество бонусов:",
        promo_create_menu
    )


@dp.message(PromoState.bonus)
async def promo_bonus_step(message: Message, state: FSMContext):

    await delete_user_message(message)

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ Введите число бонусов:",
            promo_create_menu
        )
        return

    bonus = int(message.text)

    if bonus <= 0:

        await send_menu(
            message.from_user.id,
            "❌ Количество бонусов должно быть больше 0.",
            promo_create_menu
        )
        return

    await state.update_data(bonus=bonus)

    await state.set_state(PromoState.activations)

    data = await state.get_data()

    await send_menu(
        message.from_user.id,
        f"🎁 Код: {data['code']}\n"
        f"💎 Бонусов: {bonus}\n\n"
        "🔢 Введите количество активаций:",
        promo_create_menu
    )


@dp.message(PromoState.activations)
async def promo_activations_step(message: Message, state: FSMContext):

    await delete_user_message(message)

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ Введите число активаций:",
            promo_create_menu
        )
        return

    activations = int(message.text)

    if activations <= 0:

        await send_menu(
            message.from_user.id,
            "❌ Количество активаций должно быть больше 0.",
            promo_create_menu
        )
        return

    data = await state.get_data()

    promos = load_promos()

    promos[data["code"]] = {
        "bonus": data["bonus"],
        "activations": activations,
        "used": 0
    }

    save_promos(promos)

    await state.clear()

    await send_menu(
        message.from_user.id,
        "✅ Промокод успешно создан!\n\n"
        f"🎁 Код: {data['code']}\n"
        f"💎 Бонусов: {data['bonus']}\n"
        f"🔢 Активаций: {activations}",
        promo_menu
    )


@dp.message(lambda m: m.text == "❌ Отмена")
async def promo_cancel(message: Message, state: FSMContext):

    await delete_user_message(message)

    await state.clear()

    await send_menu(
        message.from_user.id,
        "❌ Создание промокода отменено.",
        promo_menu
    )


@dp.message(lambda m: m.text == "🎁 Промокоды")
async def promo_activate_start(message: Message):

    await delete_user_message(message)

    waiting_promo.add(message.from_user.id)

    await send_menu(
        message.from_user.id,
        "🎁 Введите промокод:",
        back_menu
    )


@dp.message(lambda m: m.from_user.id in waiting_promo)
async def promo_activate(message: Message):

    user_id = message.from_user.id

    await delete_user_message(message)

    code = message.text.strip().upper()

    promos = load_promos()

    if code not in promos:

        waiting_promo.remove(user_id)

        await send_menu(
            user_id,
            "❌ Промокод не найден.\n\nПопробуйте ещё раз или вернитесь назад.",
            back_menu
        )

        return


    promo = promos[code]

    used_promos = load_json(
        "data/used_promos.json",
        {}
    )

    used_promos = load_json(
        "data/used_promos.json",
        {}
    )


    uid = str(user_id)

    if uid in used_promos and code in used_promos[uid]:

        waiting_promo.remove(user_id)

        await send_menu(
            user_id,
            "❌ Вы уже использовали этот промокод.",
            back_menu
        )

        return


    if promo["used"] >= promo["activations"]:

        waiting_promo.remove(user_id)

        await send_menu(
            user_id,
            "❌ Промокод закончился.\n\nВыберите действие:",
            back_menu
        )

        return


    points = get_points(user_id)

    points["balance"] += promo["bonus"]

    save_points(
        user_id,
        points
    )


    promo["used"] += 1

    if uid not in used_promos:
        used_promos[uid] = []

    used_promos[uid].append(code)

    save_json(
        "data/used_promos.json",
        used_promos
    )


    promos[code] = promo

    save_promos(promos)


    waiting_promo.remove(user_id)


    await send_menu(
        user_id,
        f"✅ Промокод активирован!\n\n"
        f"⭐ Получено: {promo['bonus']} баллов",
        back_menu
    )


@dp.message(lambda m: m.text == "👤 Профиль")
async def profile(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    profiles = load_json(
        "data/user_profiles.json",
        {}
    )

    profile_data = profiles.get(
        str(user_id),
        {}
    )

    registered = profile_data.get(
        "registered",
        "Неизвестно"
    )

    last_login = profile_data.get(
        "last_login",
        "Неизвестно"
    )


    stats_data = load_json(
        "data/funpay_stats.json",
        {}
    )

    user_stats = stats_data.get(
        str(user_id),
        {}
    )

    orders_total = user_stats.get(
        "orders_total",
        0
    )

    orders_done = user_stats.get(
        "orders_done",
        0
    )

    turnover_total = user_stats.get(
        "turnover_total",
        0
    )

    buyers = user_stats.get(
        "buyers",
        0
    )


    if is_admin(user_id):
        status = "👑 Админ"
    else:
        status = "👤 Пользователь"


    funpay = "✅" if os.path.exists(
        f"data/accounts/{user_id}_funpay.json"
    ) else "❌"


    playerok = "✅" if os.path.exists(
        f"data/accounts/{user_id}_playerok.json"
    ) else "❌"


    await send_menu(
        user_id,

        f"👤 Профиль\n"
        f"🆔 {user_id}\n\n"

        f"📦 Заказы: {orders_total} | ✅ {orders_done}\n"
        f"💰 Оборот: {turnover_total} ₽\n"
        f"👥 Покупатели: {buyers}\n\n"

        f"{status}\n"
        f"🛒 FunPay {funpay}  🎮 PlayerOK {playerok}\n\n"

        f"📅 {registered}\n"
        f"🕒 {last_login}",

        back_menu
    )

@dp.message(lambda m: m.text == "📋 Список промокодов")
async def promo_list(message: Message):

    if not is_admin(message.from_user.id):
        return

    await delete_user_message(message)

    promos = load_promos()

    if not promos:

        await send_menu(
            message.from_user.id,
            "📋 Промокодов пока нет.",
            promo_menu
        )

        return


    text = "📋 Список промокодов:\n\n"

    for code, promo in promos.items():

        left = promo["activations"] - promo["used"]

        text += (
            f"🎁 {code}\n"
            f"💎 Бонус: {promo['bonus']}\n"
            f"🔢 Осталось: {left}/{promo['activations']}\n\n"
        )


    await send_menu(
        message.from_user.id,
        text,
        promo_menu
    )


@dp.message(lambda m: m.text == "💰 Выдать рубли")
async def add_points_start(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await delete_user_message(message)

    await state.clear()

    await state.set_state(
        PointsState.add_user
    )

    await send_menu(
        message.from_user.id,
        "💰 Выдача рублей\n\nВведите ID пользователя:",
        back_menu
    )


@dp.message(PointsState.add_user)
async def add_points_get_user(message: Message, state: FSMContext):

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ ID должен быть числом.\n\nВведите ID пользователя:",
            back_menu
        )

        return


    await state.update_data(
        target_id=message.text
    )


    await state.set_state(
        PointsState.add_amount
    )


    await send_menu(
        message.from_user.id,
        f"👤 Пользователь: {message.text}\n\n"
        "⭐ Введите количество баллов:",
        back_menu
    )


@dp.message(lambda m: m.text == "➖ Забрать рубли")
async def remove_points_start(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await delete_user_message(message)

    await state.clear()

    await state.set_state(
        PointsState.remove_user
    )

    await send_menu(
        message.from_user.id,
        "➖ Снятие рублей\n\nВведите ID пользователя:",
        back_menu
    )

@dp.message(PointsState.add_amount)
async def add_points_finish(message: Message, state: FSMContext):

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ Введите количество рублей числом:",
            back_menu
        )

        return


    data = await state.get_data()

    target_id = int(
        data["target_id"]
    )

    amount = int(
        message.text
    )


    points = get_points(
        target_id
    )

    points["balance"] += amount

    save_points(
        target_id,
        points
    )


    await state.clear()


    await send_menu(
        message.from_user.id,

        f"✅ Баланс пополнен\n\n"
        f"👤 ID: {target_id}\n"
        f"💰 Добавлено: {amount} ₽",

        points_menu
    )

@dp.message(PointsState.remove_user)
async def remove_points_get_user(message: Message, state: FSMContext):

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ ID должен быть числом.\n\nВведите ID пользователя:",
            back_menu
        )

        return


    await state.update_data(
        target_id=message.text
    )


    await state.set_state(
        PointsState.remove_amount
    )


    await send_menu(
        message.from_user.id,
        f"👤 Пользователь: {message.text}\n\n"
        "➖ Введите количество баллов для снятия:",
        back_menu
    )


@dp.message(PointsState.remove_amount)
async def remove_points_finish(message: Message, state: FSMContext):

    if not message.text.isdigit():

        await send_menu(
            message.from_user.id,
            "❌ Введите количество баллов числом:",
            back_menu
        )

        return


    data = await state.get_data()

    target_id = int(data["target_id"])

    amount = int(message.text)


    points = get_points(target_id)

    points["balance"] -= amount


    if points["balance"] < 0:
        points["balance"] = 0


    save_points(
        target_id,
        points
    )


    await state.clear()


    await send_menu(
        message.from_user.id,
        f"✅ Баланс снят\n\n"
        f"👤 ID: {target_id}\n"
        f"➖ Убрано: {amount}",
        points_menu
    )




# =========================
# Интервал
# =========================

@dp.message(
    lambda m: m.text in [
        "⚡ 30 секунд",
        "⏱ 60 секунд",
        "🐢 120 секунд"
    ]
)
async def interval(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id


    values = {

        "⚡ 30 секунд": 30,

        "⏱ 60 секунд": 60,

        "🐢 120 секунд": 120

    }


    settings = load_json(
        f"data/settings/{user_id}.json",
        {}
    )


    settings["interval"] = values[
        message.text
    ]


    save_json(
        f"data/settings/{user_id}.json",
        settings
    )


    await send_answer(
        user_id,

        f"✅ Интервал установлен:\n\n"
        f"⏱ {values[message.text]} секунд"
    )


# =========================
# Промокод
# =========================

@dp.message(lambda m: m.text and "Промокод" in m.text)
async def promo(message: Message):

    user_id = message.from_user.id

    await delete_user_message(message)

    waiting_promo.add(user_id)

    await send_menu(
        user_id,
        "🎁 Введите ваш промокод:",
        back_menu
    )


# =========================
# Запуск рассылки
# =========================

@dp.message(
    lambda m: m.text == "📢 Рассылка"
)
async def broadcast_start(message: Message):

    user_id = message.from_user.id


    if not is_admin(user_id):
        return


    await delete_user_message(
        message
    )


    broadcast_wait.add(
        user_id
    )


    await send_menu(
        user_id,

        "📢 Рассылка\n\n"
        "Отправьте сообщение, которое нужно отправить всем пользователям.\n\n"
        "Для отмены нажмите ⬅️ Назад",

        broadcast_menu
    )


@dp.message(lambda m: m.text == "👑 Управление Premium")
async def pro_panel(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    await send_menu(
        user_id,

        "⭐ Управление Premium\n\n"
        "Выберите действие:",

        premium_menu
    )


# =========================
# Список Premium
# =========================

@dp.message(lambda m: m.text == "📋 Список Premium")
async def pro_list(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    if not is_admin(user_id):
        return


    plans = load_json(
        "data/plans.json",
        {}
    )


    text = "⭐ Пользователи Premium\n\n"


    count = 0


    for uid, plan in plans.items():

        if plan == "premium":

            text += f"👤 {uid}\n"

            count += 1


    if count == 0:

        text += "Пользователей с Premium пока нет."


    else:

        text += (
            f"\n\nВсего Premium: {count}"
        )


    await send_menu(
        user_id,

        text,

        premium_menu
    )


# =========================
# Заказы (админ)
# =========================

@dp.message(
    lambda m: m.text == "📦 Заказы"
)
async def orders(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    if not is_admin(user_id):
        return


    try:

        with open(
            "data/last_order.txt",
            "r",
            encoding="utf-8"
        ) as file:

            order = file.read()


        await send_menu(
            user_id,

            "📦 Последний заказ:\n\n"
            + order,

            back_menu
        )


    except:

        await send_menu(
            user_id,

            "📭 Заказов пока нет.",

            back_menu
        )


# =========================
# Аккаунты (админ)
# =========================

@dp.message(
    lambda m: m.text == "📱 Аккаунты"
)
async def admin_accounts(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id


    if not is_admin(user_id):
        return


    accounts = load_json(
        "data/accounts.json",
        []
    )


    if not accounts:

        await send_menu(
            user_id,

            "📱 Аккаунты\n\n"
            "Подключённых аккаунтов нет.",

            back_menu
        )

        return


    text = (
        "📱 Подключённые аккаунты:\n\n"
    )


    for acc in accounts:

        text += (
            f"• {acc}\n"
        )


    await send_menu(
        user_id,

        text,

        back_menu
    )


# =========================
# Админ магазин
# =========================

shop_admin_menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="➕ Добавить товар")
        ],

        [
            KeyboardButton(text="➖ Удалить товар")
        ],

        [
            KeyboardButton(text="📋 Список товаров")
        ],

        [
            KeyboardButton(text="⬅️ Назад")
        ]

    ],
    resize_keyboard=True
)


@dp.message(
    lambda m: m.text == "🛒 Магазин"
)
async def admin_shop(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id


    if not is_admin(user_id):
        return


    await send_menu(
        user_id,

        "🛒 Управление магазином\n\n"
        "Выберите действие:",

        shop_admin_menu
    )


# =========================
# Список товаров (админ)
# =========================

@dp.message(
    lambda m: m.text == "📋 Список товаров"
)
async def shop_list(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id


    if not is_admin(user_id):
        return


    products = load_json(
        "data/shop.json",
        []
    )


    if not products:

        await send_menu(
            user_id,

            "🛒 Магазин пуст.",

            shop_admin_menu
        )

        return


    text = "📋 Товары магазина\n\n"


    for item in products:

        text += (
            f"🆔 ID: {item['id']}\n"
            f"📦 {item['name']}\n"
            f"⭐ Цена: {item['price']}\n"
            f"📝 {item['description']}\n"
            "━━━━━━━━━━━━\n"
        )


    await send_menu(
        user_id,

        text,

        shop_admin_menu
    )


# =========================
# Добавить товар в магазин
# =========================

@dp.message(
    lambda m: m.text == "➕ Добавить товар"
)
async def add_shop_start(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id


    if not is_admin(user_id):
        return


    waiting_shop_add.add(
        user_id
    )


    await send_menu(
        user_id,

        "➕ Добавление товара\n\n"
        "Отправьте данные в формате:\n\n"
        "Название\n"
        "Цена\n"
        "Описание",

        back_menu
    )


@dp.message(
    lambda m: m.from_user.id in waiting_shop_add
)
async def shop_add_text(message: Message):

    user_id = message.from_user.id


    await delete_user_message(
        message
    )


    lines = message.text.split("\n")


    if len(lines) < 3:

        await send_menu(
            user_id,

            "❌ Нужно 3 строки:\n\n"
            "Название\n"
            "Цена\n"
            "Описание",

            shop_admin_menu
        )

        return


    try:

        price = int(
            lines[1]
        )

    except:

        await send_menu(
            user_id,

            "❌ Цена должна быть числом",

            shop_admin_menu
        )

        return



    products = load_json(
        "data/shop.json",
        []
    )


    new_id = 1


    if products:

        new_id = max(
            x["id"] for x in products
        ) + 1



    products.append(
        {
            "id": new_id,
            "name": lines[0],
            "price": price,
            "description": lines[2]
        }
    )


    save_json(
        "data/shop.json",
        products
    )


    waiting_shop_add.remove(
        user_id
    )


    await send_menu(
        user_id,

        "✅ Товар добавлен!",

        shop_admin_menu
    )


@dp.message(
    lambda m: m.text == "➖ Удалить товар"
)
async def shop_delete_start(message: Message):

    await delete_user_message(
        message
    )

    user_id = message.from_user.id

    if not is_admin(user_id):
        return


    waiting_shop_delete.add(
        user_id
    )


    await send_menu(
        user_id,

        "➖ Удаление товара\n\n"
        "Введите ID товара:",

        back_menu
    )


@dp.message(
    lambda m: m.from_user.id in waiting_shop_delete
)
async def shop_delete_handler(message: Message):

    user_id = message.from_user.id

    await delete_user_message(
        message
    )

    try:
        product_id = int(message.text)

    except:

        await send_menu(
            user_id,
            "❌ Введите только ID товара",
            back_menu
        )

        return


    products = load_json(
        "data/shop.json",
        []
    )


    new_products = []

    deleted = False


    for item in products:

        if int(item["id"]) == product_id:

            deleted = True

        else:

            new_products.append(item)


    if deleted:

        save_json(
            "data/shop.json",
            new_products
        )


        text = (
            "✅ Товар удалён\n\n"
            f"🆔 ID: {product_id}"
        )

    else:

        text = "❌ Товар не найден"


    waiting_shop_delete.discard(
        user_id
    )


    await send_menu(
        user_id,
        text,
        shop_admin_menu
    )


@dp.message(
    lambda m: m.text == "🛒 Наш FunPay"
)
async def our_funpay(message: Message):

    await delete_user_message(
        message
    )


    user_id = message.from_user.id


    await send_menu(
        user_id,

        "🛒 Наш FunPay\n\n"
        "🔥 Добро пожаловать в наш магазин!\n\n"
        "✅ Быстрые сделки\n"
        "✅ Надёжный продавец\n"
        "⚡ Моментальная обработка заказов\n\n"
        "🔗 Ссылка:\n"
        "https://funpay.com/users/15143887/",

        back_menu
    )



# =========================
# Неизвестные сообщения + профиль
# =========================

@dp.message()
async def unknown(message: Message):

    user_id = message.from_user.id


# =========================
# Подключение FunPay
# =========================

    if user_id in waiting_funpay:

        waiting_funpay.remove(user_id)

        await delete_user_message(message)

        golden_key = message.text.strip()

        save_json(
            f"data/accounts/{user_id}_funpay.json",
            {
                "golden_key": golden_key
            }
        )

        await connect_account(user_id)

        await send_menu(
            user_id,

            "✅ FunPay успешно подключён!\n\n"
            "Теперь бот сможет использовать ваш аккаунт.",

            accounts_menu
        )

        return


@dp.message(
    lambda m: m.text == "📋 Мои подключения"
)
async def my_connections(message: Message):

    await delete_user_message(message)

    user_id = message.from_user.id

    text = "📋 Мои подключения\n\n"

    funpay_file = f"data/accounts/{user_id}_funpay.json"

    if os.path.exists(funpay_file):
        text += "🛒 FunPay: 🟢 Подключён\n"
    else:
        text += "🛒 FunPay: 🔴 Не подключён\n"

    playerok_file = f"data/accounts/{user_id}_playerok.json"

    if os.path.exists(playerok_file):
        text += "🎮 Playerok: 🟢 Подключён\n"
    else:
        text += "🎮 Playerok: 🔴 Не подключён\n"

    await send_menu(
        user_id,
        text,
        accounts_menu
    )



    # =========================
    # Рассылка
    # =========================

    if user_id in broadcast_wait:

        broadcast_wait.remove(user_id)

        try:
            await message.delete()
        except:
            pass

    if str(user_id) in bot_messages:

        try:

            await bot.delete_message(
                chat_id=user_id,
                message_id=bot_messages[str(user_id)]
            )

        except:

            pass



    users = load_json(
        "data/users.json",
        []
    )


    sent = 0


    for uid in users:

        print("Отправляю:", uid)


        try:

            # если отправили фото
            if message.photo:


                sent_msg = await bot.send_photo(

                    chat_id=uid,

                    photo=message.photo[-1].file_id,

                    caption=message.caption

                )


            # если отправили обычный текст
            else:


                sent_msg = await bot.send_message(

                    chat_id=uid,

                    text=message.text

                )



            bot_messages[str(uid)] = sent_msg.message_id


            sent += 1



        except Exception as e:

            print(
                "Ошибка рассылки:",
                uid,
                e
            )



    save_json(
        "data/bot_messages.json",
        bot_messages
    )



    await send_menu(

        user_id,

        "✅ Рассылка завершена\n\n"
        f"Отправлено: {sent} пользователей",

        admin_menu

    )


    return




    # =========================
    # Неизвестная команда
    # =========================

    if message.text and message.text.startswith("/"):
        return

    kb = admin_menu if is_admin(user_id) else user_menu

    await send_menu(
        user_id,
        "❓ Не понял команду.\nИспользуйте кнопки меню.",
        kb
    )

# =========================
# Запуск
# =========================

funpay_task = None
chat_task = None


async def start_bot():

    global funpay_task

    # автозапуск Market
    if os.path.exists(
        "data/accounts/8551860166_funpay.json"
    ):

        print("🟢 Автозапуск Market")

        funpay_task = asyncio.create_task(
            monitor_orders()
        )

    accounts = get_accounts()

    for account in accounts:

        asyncio.create_task(
            monitor_chat(
                account["user_id"]
            )
        )


    while True:
        try:
            await dp.start_polling(bot)

        except Exception as e:
            print("⚠️ Telegram отключен:", e)
            print("🔄 Повтор через 10 секунд...")
            await asyncio.sleep(10)

if __name__ == "__main__":

    import asyncio


    asyncio.run(
        start_bot()
    )