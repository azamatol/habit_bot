import telebot
import json
import os
from datetime import datetime, timedelta
from telebot import types

# ============ ВСТАВЬ СВОЙ ТОКЕН СЮДА ============
TOKEN = "8998847939:AAG3qJ691RLYUB0Kxjh1V0Ql723o3MG1vYg"
# ===============================================

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "users.json"


# ---------- Работа с данными ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "name": "",
            "habits": [],          # список привычек
            "done": {},            # {"2026-09-22": ["спорт", "вода"]}
            "mood": {}             # {"2026-09-22": 4}
        }
    return data[uid]


def today():
    return datetime.now().strftime("%Y-%m-%d")


# ---------- Меню-клавиатура ----------
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить привычку", "✅ Отметить")
    kb.row("📊 Статистика", "😊 Настроение")
    kb.row("📈 График настроения", "❓ Помощь")
    return kb


# ---------- /start ----------
@bot.message_handler(commands=['start'])
def start(message):
    data = load_data()
    user = get_user(data, message.chat.id)
    user["name"] = message.from_user.first_name
    save_data(data)

    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот «Привычка+» — помогаю вырабатывать полезные привычки "
        "и следить за настроением.\n\n"
        "Жми кнопки внизу или пиши /help.",
        reply_markup=main_menu()
    )


# ---------- /help ----------
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "📌 Что я умею:\n\n"
        "➕ Добавить привычку — создай новую привычку\n"
        "✅ Отметить — отметь, что выполнил сегодня\n"
        "📊 Статистика — сколько раз выполнил за неделю\n"
        "😊 Настроение — оцени настроение от 1 до 5\n"
        "📈 График настроения — картинка за 7 дней\n\n"
        "Команды: /start /help /habit /done /stats /mood",
        reply_markup=main_menu()
    )


# ---------- Добавить привычку ----------
@bot.message_handler(commands=['habit'])
@bot.message_handler(func=lambda m: m.text == "➕ Добавить привычку")
def add_habit(message):
    msg = bot.send_message(message.chat.id, "Напиши название привычки (например: спорт, вода, чтение):")
    bot.register_next_step_handler(msg, save_habit)


def save_habit(message):
    name = message.text.strip()
    if not name or name.startswith("/"):
        bot.send_message(message.chat.id, "Не понял. Попробуй ещё раз.", reply_markup=main_menu())
        return

    data = load_data()
    user = get_user(data, message.chat.id)

    if name in user["habits"]:
        bot.send_message(message.chat.id, f"Привычка «{name}» уже есть.", reply_markup=main_menu())
        return

    user["habits"].append(name)
    save_data(data)
    bot.send_message(message.chat.id, f"✅ Привычка «{name}» добавлена!", reply_markup=main_menu())


# ---------- Отметить выполнение ----------
@bot.message_handler(commands=['done'])
@bot.message_handler(func=lambda m: m.text == "✅ Отметить")
def mark_done(message):
    data = load_data()
    user = get_user(data, message.chat.id)

    if not user["habits"]:
        bot.send_message(message.chat.id, "Сначала добавь привычку ➕", reply_markup=main_menu())
        return

    kb = types.InlineKeyboardMarkup()
    for h in user["habits"]:
        kb.add(types.InlineKeyboardButton(text=h, callback_data=f"done|{h}"))
    bot.send_message(message.chat.id, "Что выполнено сегодня?", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("done|"))
def callback_done(call):
    habit = call.data.split("|", 1)[1]
    data = load_data()
    user = get_user(data, call.message.chat.id)

    day = today()
    user["done"].setdefault(day, [])
    if habit in user["done"][day]:
        bot.answer_callback_query(call.id, "Уже отмечено ✅")
        return

    user["done"][day].append(habit)
    save_data(data)
    bot.answer_callback_query(call.id, f"Отмечено: {habit} ✅")
    bot.edit_message_text(
        f"✅ «{habit}» отмечено на {day}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


# ---------- Статистика ----------
@bot.message_handler(commands=['stats'])
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    data = load_data()
    user = get_user(data, message.chat.id)

    if not user["habits"]:
        bot.send_message(message.chat.id, "Пока нет привычек.", reply_markup=main_menu())
        return

    week_ago = datetime.now() - timedelta(days=7)
    text = "📊 Статистика за 7 дней:\n\n"

    for h in user["habits"]:
        count = 0
        for day, items in user["done"].items():
            d = datetime.strptime(day, "%Y-%m-%d")
            if d >= week_ago and h in items:
                count += 1
        text += f"• {h}: {count}/7\n"

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


# ---------- Настроение ----------
@bot.message_handler(commands=['mood'])
@bot.message_handler(func=lambda m: m.text == "😊 Настроение")
def mood(message):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("1 😞", callback_data="mood|1"),
        types.InlineKeyboardButton("2 😐", callback_data="mood|2"),
        types.InlineKeyboardButton("3 🙂", callback_data="mood|3"),
        types.InlineKeyboardButton("4 😃", callback_data="mood|4"),
        types.InlineKeyboardButton("5 🤩", callback_data="mood|5"),
    )
    bot.send_message(message.chat.id, "Как настроение сегодня?", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("mood|"))
def callback_mood(call):
    value = int(call.data.split("|")[1])
    data = load_data()
    user = get_user(data, call.message.chat.id)
    user["mood"][today()] = value
    save_data(data)

    bot.answer_callback_query(call.id, f"Записано: {value}/5")
    bot.edit_message_text(
        f"😊 Настроение на {today()}: {value}/5",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


# ---------- График настроения ----------
@bot.message_handler(commands=['chart'])
@bot.message_handler(func=lambda m: m.text == "📈 График настроения")
def chart(message):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        bot.send_message(
            message.chat.id,
            "Для графика нужна библиотека matplotlib.\n"
            "Установи: pip install matplotlib",
            reply_markup=main_menu()
        )
        return

    data = load_data()
    user = get_user(data, message.chat.id)

    if not user["mood"]:
        bot.send_message(message.chat.id, "Пока нет данных о настроении.", reply_markup=main_menu())
        return

    days = []
    values = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        days.append(d[5:])  # MM-DD
        values.append(user["mood"].get(d, 0))

    plt.figure(figsize=(6, 3))
    plt.plot(days, values, marker="o", color="#4A90E2")
    plt.ylim(0, 5)
    plt.title("Настроение за 7 дней")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("mood_chart.png", dpi=120)
    plt.close()

    with open("mood_chart.png", "rb") as f:
        bot.send_photo(message.chat.id, f, caption="📈 Твоё настроение за неделю")


# ---------- Запуск ----------
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()