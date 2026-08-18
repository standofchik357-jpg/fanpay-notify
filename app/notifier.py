from app.bot_instance import bot
from app.storage import order_messages


async def notify(user_id, text):

    msg = await bot.send_message(
        chat_id=user_id,
        text=text
    )

    order_messages[user_id] = msg.message_id