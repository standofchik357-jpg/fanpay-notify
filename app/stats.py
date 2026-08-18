from datetime import datetime

stats = {
    "orders": 0,
    "new_orders": 0,
    "money": 0,
    "buyers": 0,
    "chats": 0,
    "reminders": 0,
    "autoreplies": 0,
    "start_time": datetime.now()
}


def save_stats():

    import json
    import os

    os.makedirs(
        "data",
        exist_ok=True
    )

    data = stats.copy()

    data["start_time"] = data["start_time"].strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with open(
        "data/stats.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )