const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
}

const user = tg?.initDataUnsafe?.user;


// =========================
// Пользователь
// =========================

if (user) {

    const name =
        user.first_name ||
        user.username ||
        "Пользователь";

    document.getElementById("username").textContent = name;

} else {

    document.getElementById("username").textContent =
        "Тестовый пользователь";
}


// =========================
// Загрузка данных
// =========================

async function loadUserData() {

    // Пока открываем через обычный браузер
    // используем тестовый ID
    const userId = user?.id || 8551860166;

    try {

        const response = await fetch(
            `/api/user/${userId}`
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data = await response.json();

        console.log(
            "Данные пользователя:",
            data
        );


        // =========================
        // Баланс
        // =========================

        document.getElementById(
            "balance"
        ).textContent = data.balance;


        // =========================
        // Тариф
        // =========================

        const planElement =
            document.querySelector(".plan");

        if (data.plan === "premium") {

            planElement.textContent =
                "⭐ PREMIUM";

        } else {

            planElement.textContent =
                "🆓 FREE";
        }


        // =========================
        // FunPay
        // =========================

        const services =
            document.querySelectorAll(".status-card");

        if (services.length >= 1) {

            const status =
                services[0].querySelector(
                    ".service-status"
                );

            if (data.funpay) {

                status.textContent =
                    "Подключён";

            } else {

                status.textContent =
                    "Не подключён";
            }
        }


        // =========================
        // PlayerOK
        // =========================

        if (services.length >= 2) {

            const status =
                services[1].querySelector(
                    ".service-status"
                );

            if (data.playerok) {

                status.textContent =
                    "Подключён";

            } else {

                status.textContent =
                    "Не подключён";
            }
        }

    } catch (error) {

        console.error(
            "Ошибка загрузки данных:",
            error
        );
    }
}


// =========================
// Запуск
// =========================

loadUserData();