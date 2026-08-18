import asyncio
import json
import os
from datetime import datetime

from playwright.async_api import async_playwright
from app.stats import stats


CHAT_DB = "data/chat_messages.json"
REMINDERS_FILE = "data/review_reminders.json"

MY_FUNPAY_USER_ID = "15143887"


AUTO_REPLY_COOLDOWN = 30 * 60
REVIEW_REMINDER_DELAY = 2 * 60 * 60


AUTO_REPLY = (
    "👋 Здравствуйте! Спасибо за обращение 😊\n\n"
    "Ваше сообщение получено.\n"
    "Если я онлайн — скоро отвечу вам.\n"
    "Если сейчас занят другим заказом — вернусь, "
    "как только освобожусь.\n\n"
    "🟢 Market Notify"
)


REVIEW_REPLY = (
    "👋 Небольшое напоминание 😊\n\n"
    "Если всё прошло хорошо, "
    "буду благодарен за ваш отзыв ⭐\n\n"
    "Спасибо за покупку!\n\n"
    "🟢 Market Notify"
)


# =========================================================
# CHAT DATABASE
# =========================================================

def load_messages():
    if not os.path.exists(CHAT_DB):
        return {}

    try:
        with open(
            CHAT_DB,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception as e:
        print(
            "❌ Ошибка загрузки базы чатов:",
            repr(e)
        )

    return {}


def save_messages(data):
    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        CHAT_DB,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def remember_message(
    username,
    message,
    saved
):
    if username not in saved:
        saved[username] = {
            "messages": [],
            "last_answer": None
        }

    messages = saved[username].setdefault(
        "messages",
        []
    )

    if message not in messages:
        messages.append(message)


def message_was_seen(
    username,
    message,
    saved
):
    if username not in saved:
        return False

    return message in saved[username].get(
        "messages",
        []
    )


def can_send_auto_reply(
    username,
    saved
):
    if username not in saved:
        return True

    last_answer = saved[username].get(
        "last_answer"
    )

    if not last_answer:
        return True

    try:
        last_time = datetime.strptime(
            last_answer,
            "%Y-%m-%d %H:%M:%S"
        )

        passed = (
            datetime.now() - last_time
        ).total_seconds()

        return passed >= AUTO_REPLY_COOLDOWN

    except Exception:
        return True


def update_answer_time(
    username,
    saved
):
    if username not in saved:
        saved[username] = {
            "messages": [],
            "last_answer": None
        }

    saved[username]["last_answer"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


# =========================================================
# FUNPAY MESSAGE HELPERS
# =========================================================

async def is_my_message(
    message_element
):
    try:
        author_link = (
            message_element
            .locator(
                "a.chat-msg-author-link"
            )
            .first
        )

        if not await author_link.count():
            return False

        href = await author_link.get_attribute(
            "href"
        )

        if not href:
            return False

        return MY_FUNPAY_USER_ID in href

    except Exception:
        return False


async def get_message_text(
    message_element
):
    try:
        text_element = (
            message_element
            .locator(
                ".chat-msg-text"
            )
            .first
        )

        if not await text_element.count():
            return None

        text = (
            await text_element
            .inner_text()
        ).strip()

        return text or None

    except Exception:
        return None


# =========================================================
# SEND MESSAGE
# =========================================================

async def send_message(
    page,
    text
):
    try:
        print(
            "📤 Ищу поле сообщения..."
        )

        textarea = (
            page
            .locator("textarea")
            .last
        )

        await textarea.wait_for(
            timeout=10000
        )

        await textarea.fill(text)

        button = (
            page
            .locator(
                "button[type='submit']"
            )
            .last
        )

        if await button.count():
            await button.click()
        else:
            await textarea.press(
                "Enter"
            )

        await page.wait_for_timeout(
            1200
        )

        print(
            "✅ Сообщение отправлено"
        )

        return True

    except Exception as e:
        print(
            "❌ Ошибка отправки:",
            repr(e)
        )

        return False


# =========================================================
# REVIEW REMINDERS
# =========================================================

def load_reminders():
    if not os.path.exists(
        REMINDERS_FILE
    ):
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
            "❌ Ошибка загрузки напоминаний:",
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


def get_ready_reminders():
    reminders = load_reminders()

    result = []

    now = datetime.now()

    for key, info in reminders.items():

        if not isinstance(info, dict):
            continue

        try:
            saved_time = datetime.strptime(
                info["time"],
                "%Y-%m-%d %H:%M:%S"
            )

            passed = (
                now - saved_time
            ).total_seconds()

            if passed >= REVIEW_REMINDER_DELAY:
                result.append({
                    "key": key,
                    "user_id": info.get(
                        "user_id"
                    ),
                    "username": info.get(
                        "username"
                    ),
                    "order": info.get(
                        "order"
                    )
                })

        except Exception:
            continue

    return result


def delete_reminder(key):
    reminders = load_reminders()

    if key in reminders:
        del reminders[key]
        save_reminders(reminders)


def remove_review_reminder(username):
    reminders = load_reminders()

    changed = False

    for key in list(reminders.keys()):

        info = reminders[key]

        if not isinstance(info, dict):
            continue

        if (
            str(
                info.get("username", "")
            ).lower()
            == username.lower()
        ):
            del reminders[key]
            changed = True

    if changed:
        save_reminders(reminders)

        print(
            "⭐ Отзыв найден — "
            "напоминание удалено:",
            username
        )


# =========================================================
# FIND CHAT
# =========================================================

async def open_chat_by_username(
    page,
    username
):
    try:
        chats = page.locator(
            "a.contact-item"
        )

        count = await chats.count()

        stats["chats"] = count

        for index in range(count):

            try:
                chat = chats.nth(index)

                text = await chat.inner_text()

                name = (
                    text
                    .split("\n")[0]
                    .strip()
                )

                if (
                    name.lower()
                    == username.lower()
                ):
                    await chat.click()

                    await page.wait_for_timeout(
                        500
                    )

                    return True

            except Exception:
                continue

    except Exception:
        pass

    return False


# =========================================================
# REVIEW REMINDER PROCESSING
# =========================================================

async def process_review_reminders(
    page
):
    reminders = get_ready_reminders()

    if not reminders:
        return

    for reminder in reminders:

        username = reminder["username"]
        key = reminder["key"]

        if not username:
            delete_reminder(key)
            continue

        print(
            "⭐ Напоминание об отзыве:",
            username
        )

        try:
            opened = await open_chat_by_username(
                page,
                username
            )

            if not opened:
                print(
                    "⚠️ Чат для напоминания "
                    "не найден:",
                    username
                )
                continue

            success = await send_message(
                page,
                REVIEW_REPLY
            )

            if success:

                stats["reminders"] = (
                    stats.get(
                        "reminders",
                        0
                    ) + 1
                )

                delete_reminder(key)

                print(
                    "⭐ Напоминание отправлено:",
                    username
                )

        except Exception as e:
            print(
                "❌ Ошибка напоминания:",
                repr(e)
            )


# =========================================================
# CHAT MONITOR
# =========================================================

async def monitor_chat(user_id):

    print()
    print(
        "🔥 MARKET NOTIFY START:",
        user_id
    )

    saved = load_messages()

    baseline_initialized = False

    async with async_playwright() as p:

        browser = None

        try:

            print(
                "🌐 Запускаю FunPay с сохранённой сессией..."
            )

            browser = await p.chromium.launch(
                headless=True
            )

            context = await browser.new_context(
                storage_state=(
                    f"data/accounts/{user_id}_funpay.json"
                )
            )

            page = await context.new_page()

            await page.goto(
                "https://funpay.com/chat/",
                wait_until="domcontentloaded"
            )

            await page.wait_for_timeout(
                3000
            )

            print(
                "🟢 FunPay открыт через session"
            )

            print(
                "🟢 Мониторинг чатов запущен"
            )

            while True:

                try:

                    await process_review_reminders(
                        page
                    )

                    chats = page.locator(
                        "a.contact-item"
                    )

                    chat_count = await chats.count()

                    stats["chats"] = chat_count

                    print(
                        "💬 Чатов найдено:",
                        chat_count
                    )

                    for chat_index in range(
                        chat_count
                    ):

                        try:

                            chat = chats.nth(
                                chat_index
                            )

                            chat_text = (
                                await chat.inner_text()
                            )

                            username = (
                                chat_text
                                .split("\n")[0]
                                .strip()
                            )

                            if not username:
                                continue

                            if username.lower() == "funpay":
                                continue

                            await chat.click()

                            await page.wait_for_timeout(
                                300
                            )

                            messages = page.locator(
                                ".chat-message"
                            )

                            message_count = (
                                await messages.count()
                            )

                            if message_count == 0:
                                continue

                            # -------------------------------------------------
                            # Сначала проверяем САМОЕ ПОСЛЕДНЕЕ сообщение.
                            # Если оно наше — этот чат полностью пропускаем.
                            # -------------------------------------------------

                            last_message_element = (
                                messages.nth(
                                    message_count - 1
                                )
                            )

                            if await is_my_message(
                                last_message_element
                            ):
                                print(
                                    "⏭ Последнее сообщение моё, пропускаю:",
                                    username
                                )
                                continue

                            # -------------------------------------------------
                            # Ищем последнее сообщение покупателя.
                            # -------------------------------------------------

                            last_user_message = None

                            for i in range(
                                message_count - 1,
                                -1,
                                -1
                            ):

                                msg = messages.nth(i)

                                if await is_my_message(
                                    msg
                                ):
                                    continue

                                text = await get_message_text(
                                    msg
                                )

                                if text:

                                    last_user_message = text
                                    break

                            if not last_user_message:
                                continue

                            print(
                                "👤",
                                username,
                                ":",
                                last_user_message
                            )

                            low = (
                                last_user_message
                                .lower()
                            )

                            # -------------------------------------------------
                            # Проверяем сообщение про отзыв.
                            # -------------------------------------------------

                            if (
                                "отзыв" in low
                                or "оставил отзыв" in low
                                or "написал отзыв" in low
                            ):

                                remove_review_reminder(
                                    username
                                )

                            # -------------------------------------------------
                            # Если это сообщение уже обрабатывали —
                            # пропускаем.
                            # -------------------------------------------------

                            if message_was_seen(
                                username,
                                last_user_message,
                                saved
                            ):
                                continue

                        # -------------------------------------------------
                        # При первом запуске существующие сообщения
                        # запоминаем, но НЕ отвечаем на них.
                        # -------------------------------------------------



                            print(
                                "🆕 НОВОЕ СООБЩЕНИЕ:",
                                username
                            )

                            remember_message(
                                username,
                                last_user_message,
                                saved
                            )

                            save_messages(
                                saved
                            )

                            # -------------------------------------------------
                            # Cooldown автоответа.
                            # -------------------------------------------------

                            if not can_send_auto_reply(
                                username,
                                saved
                            ):

                                print(
                                    "⏱ Cooldown:",
                                    username
                                )

                                continue

                            # -------------------------------------------------
                            # Ждём 5 секунд.
                            # За это время пользователь может написать
                            # сообщение сам.
                            # -------------------------------------------------

                            print(
                                "⏳ Жду 5 секунд..."
                            )

                            await asyncio.sleep(
                                5
                            )

                            # -------------------------------------------------
                            # После ожидания заново получаем сообщения.
                            # Это важно, чтобы не ответить поверх твоего
                            # собственного сообщения.
                            # -------------------------------------------------

                            current_messages = page.locator(
                                ".chat-message"
                            )

                            current_count = (
                                await current_messages.count()
                            )

                            if current_count == 0:
                                continue

                            current_last_message = (
                                current_messages.nth(
                                    current_count - 1
                                )
                            )

                            if await is_my_message(
                                current_last_message
                            ):

                                print(
                                    "⏭ После ожидания последнее "
                                    "сообщение моё — не отвечаю:",
                                    username
                                )

                                continue

                            # -------------------------------------------------
                            # Отправляем автоответ.
                            # -------------------------------------------------

                            success = await send_message(
                                page,
                                AUTO_REPLY
                            )

                            if not success:
                                continue

                            remember_message(
                                username,
                                AUTO_REPLY,
                                saved
                            )

                            update_answer_time(
                                username,
                                saved
                            )

                            save_messages(
                                saved
                            )

                            stats["autoreplies"] = (
                                stats.get(
                                    "autoreplies",
                                    0
                                ) + 1
                            )

                            print(
                                "🤖 Автоответ отправлен:",
                                username
                            )

                        except Exception as e:

                            print(
                                "⚠️ Ошибка обработки чата:",
                                repr(e)
                            )

                            continue

                    # -------------------------------------------------
                    # После первого полного прохода включаем обработку
                    # новых сообщений.
                    # -------------------------------------------------

                    if not baseline_initialized:

                        baseline_initialized = True

                        save_messages(
                            saved
                        )

                        print(
                            "🛡️ Базовая загрузка чата завершена"
                        )

                        print(
                            "🟢 Автоответ включён"
                        )

                except Exception as e:

                    print(
                        "❌ Ошибка мониторинга:",
                        repr(e)
                    )

                await asyncio.sleep(
                    5
                )

        except Exception as e:

            print(
                "❌ Ошибка запуска FunPay:",
                repr(e)
            )

        finally:

            if browser:

                try:

                    await browser.close()

                except Exception:

                    pass