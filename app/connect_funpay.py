from playwright.async_api import async_playwright
import os
import asyncio


async def connect_account(user_id):

    os.makedirs(
        "data/accounts",
        exist_ok=True
    )

    os.makedirs(
        "edge_profiles",
        exist_ok=True
    )


    profile_dir = (
        f"edge_profiles/{user_id}"
    )


    os.makedirs(
        profile_dir,
        exist_ok=True
    )


    session_file = (
        f"data/accounts/{user_id}_funpay.json"
    )


    async with async_playwright() as p:

        print("🟡 Запускаю Edge...")


        context = await p.chromium.launch_persistent_context(

            user_data_dir=profile_dir,

            channel="msedge",

            headless=True,

            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )


        print("🟢 Edge запущен")


        page = await context.new_page()


        print("🟢 Новая вкладка создана")


        await page.goto(
            "https://funpay.com/",
            wait_until="domcontentloaded",
            timeout=30000
        )


        print("🟢 FunPay открыт")


        print("=" * 50)
        print(
            "Войдите в свой FunPay аккаунт."
        )
        print(
            "После входа нажмите Enter."
        )
        print("=" * 50)


        await asyncio.to_thread(
            input
        )


        print("💾 Сохраняю сессию...")


        await context.storage_state(
            path=session_file
        )


        print("✅ Сессия сохранена")

        print(
            "Файл:",
            session_file
        )


        await context.close()