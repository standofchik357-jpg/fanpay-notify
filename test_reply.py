from app.funpay_chat import AUTO_REPLY


print()
print("==============================================")
print("🤖 ТЕСТ АВТООТВЕТА FUNPAY")
print("==============================================")
print("❌ Браузер не запускается")
print("❌ Сообщения не отправляются")
print("❌ FunPay не трогается")
print()
print("Введи сообщение покупателя")
print("exit - выход")
print("==============================================")
print()


while True:

    text = input(
        "💬 Сообщение покупателя: "
    ).strip()


    if text.lower() == "exit":
        print("👋 Тест завершён")
        break


    if not text:
        continue


    print()
    print("👤 Покупатель написал:")
    print(text)


    print()
    print("🤖 Бот должен ответить:")
    print()
    print(AUTO_REPLY)

    print()
    print("----------------------------------------------")