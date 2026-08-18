from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI()


# =========================
# Вспомогательная функция
# =========================

def load_json(path, default):

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:
        return default


# =========================
# API пользователя
# =========================

@app.get("/api/user/{user_id}")
async def get_user(user_id: int):

    uid = str(user_id)

    # Баланс
    points = load_json(
        f"data/points/{uid}.json",
        {
            "balance": 0,
            "last_spin": None
        }
    )

    # Тариф
    plans = load_json(
        "data/plans.json",
        {}
    )

    plan_data = plans.get(
        uid,
        "free"
    )

    if isinstance(plan_data, dict):
        plan = plan_data.get(
            "plan",
            "free"
        )
    else:
        plan = plan_data

    # FunPay
    funpay = os.path.exists(
        f"data/accounts/{uid}_funpay.json"
    )

    # PlayerOK
    playerok = os.path.exists(
        f"data/accounts/{uid}_playerok.json"
    )

    return {
        "user_id": user_id,
        "balance": points.get("balance", 0),
        "plan": plan,
        "funpay": funpay,
        "playerok": playerok
    }


# =========================
# Mini App
# =========================

app.mount(
    "/",
    StaticFiles(
        directory="miniapp",
        html=True
    ),
    name="miniapp"
)