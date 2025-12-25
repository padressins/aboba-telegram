import telebot
from telebot import types
import json
import os
from datetime import datetime

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("8469702127:AAGXk3qjK42rEEj-AjTsmNfkp8l_hK7zn-M")
ADMIN_ID = 844810573  # Твой ID
GROUP_ID = -1003636379042  # ID группы саппорта
bot = telebot.TeleBot("8469702127:AAGXk3qjK42rEEj-AjTsmNfkp8l_hK7zn-M")

# === ФАЙЛЫ ===
USERS_FILE = os.path.join("data", "users.json")
RATES_FILE = os.path.join("data", "rates.json")
REFERRALS_FILE = os.path.join("data", "referrals.json")
PAYMENT_FILE = os.path.join("data", "payment.txt")

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
admin_sessions = set()
user_states = {}

# === ФУНКЦИИ ===
def load_json(file, default=None):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default or {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# === ОСНОВНОЙ КОД ===

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    users = load_json(USERS_FILE, {})
    
    # Проверяем рефералку
    ref_id = None
    if len(message.text.split()) > 1:
        ref_param = message.text.split()[1]
        if ref_param.startswith("ref_"):
            ref_id = ref_param.replace("ref_", "")
    
    # Если новый пользователь
    if str(user_id) not in users:
        users[str(user_id)] = {
            "username": username,
            "ref_by": ref_id,
            "transactions": [],
            "created_at": datetime.now().isoformat()
        }
        save_json(USERS_FILE, users)
    
    # Показываем соглашение
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Согласен, перейти в бота", callback_data="agree")
    btn2 = types.InlineKeyboardButton("Пользовательское соглашение", url="https://telegra.ph/Ps")
    markup.add(btn1, btn2)
    
    bot.send_message(
        message.chat.id,
        "Дальнейшие действия в боте будут подтверждать, что <b>Вы полностью ознакомились с правилами сервиса:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "agree")
def handle_agree(call):
    user_id = call.from_user.id
    
    # Показываем главное меню
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Мой профиль", callback_data="profile")
    btn2 = types.InlineKeyboardButton("Обмен", callback_data="exchange")
    btn3 = types.InlineKeyboardButton("Партнёрская программа", callback_data="referral")
    btn4 = types.InlineKeyboardButton("Техподдержка", callback_data="support")
    markup.add(btn1, btn2).add(btn3, btn4)
    
    bot.edit_message_text(
        "Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def show_profile(call):
    user_id = str(call.from_user.id)
    users = load_json(USERS_FILE, {})
    
    user_data = users.get(user_id, {})
    transactions = user_data.get("transactions", [])
    
    # Считаем только подтверждённые транзакции
    confirmed_tx = [tx for tx in transactions if tx.get("status") == "confirmed"]
    total_amount = sum(tx.get("amount_rub", 0) for tx in confirmed_tx)
    
    text = f"📊 <b>Ваш профиль:</b>\n"
    text += f"Успешных транзакций: {len(confirmed_tx)}\n"
    text += f"Сумма всех транзакций: {total_amount} ₽\n\n"
    
    if confirmed_tx:
        text += "<b>История транзакций:</b>\n"
        for tx in confirmed_tx:
            text += f"• {tx['amount_btc']} BTC → {tx['amount_rub']} ₽ ({tx['date']})\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("Назад", callback_data="main_menu")
    btn_home = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    markup.add(btn_back, btn_home)
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "exchange")
def handle_exchange(call):
    user_id = call.from_user.id
    
    # Показываем фото и сообщение
    with open("images/btc.jpg", "rb") as photo:
        bot.send_photo(
            call.message.chat.id,
            photo,
            caption="<i>*Минимум 0.00025 и не больше 0.0015 BTC</i>",
            parse_mode="HTML"
        )
    
    # Ждём ввод суммы
    user_states[user_id] = "waiting_amount"
    bot.send_message(call.message.chat.id, "Введите сумму BTC:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_amount")
def handle_amount(message):
    try:
        amount = float(message.text)
        if amount < 0.00025:
            bot.reply_to(message, "⛔️ <b>Минимум 0.00025 BTC,</b> введите еще раз...", parse_mode="HTML")
            return
        if amount > 0.0015:
            bot.reply_to(message, "<b>Максимум 0.0015 BTC,</b> введите еще раз...\n\nДля более крупных пополнений обращайтесь напрямую к саппорту! - @Aboba_Exchange", parse_mode="HTML")
            return
        
        # Сохраняем сумму
        user_states[message.from_user.id] = {"state": "waiting_wallet", "amount": amount}
        
        # Показываем фото кошелька
        with open("images/wallet.jpg", "rb") as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption="<b>Внимательно проверяте введенные данные</b>",
                parse_mode="HTML"
            )
        
        bot.send_message(message.chat.id, "Введите кошелек:")
        
    except ValueError:
        bot.reply_to(message, "Введите число в формате 0.00025")

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and user_states[message.from_user.id].get("state") == "waiting_wallet")
def handle_wallet(message):
    user_id = message.from_user.id
    data = user_states[user_id]
    amount = data["amount"]
    
    # Получаем курс
    rates = load_json(RATES_FILE, {"BTC": 7000000})
    rate = rates["BTC"]
    sum_moment = amount * rate * 1.2
    sum_delay = amount * rate * 1.1
    
    # Сохраняем кошелек
    user_states[user_id] = {"state": "waiting_payment_method", "amount": amount, "wallet": message.text}
    
    # Показываем выбор способа
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(f"Моментально: {round(sum_moment)} ₽", callback_data="method_moment")
    btn2 = types.InlineKeyboardButton(f"С ожиданием: {round(sum_delay)} ₽", callback_data="method_delay")
    
    bot.send_message(
        message.chat.id,
        f"Вы выбрали {amount} BTC.\n"
        f"Текущий курс: {rate} ₽ за 1 BTC.\n"
        f"Ваш кошелек {message.text}\n\n"
        f"Внимательно проверьте введенные вами данные\n\n"
        f"Выберите способ пополнения:\n"
        f"• Моментально: {round(sum_moment)} ₽\n"
        f"• С ожиданием: {round(sum_delay)} ₽",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["method_moment", "method_delay"])
def handle_payment_method(call):
    user_id = call.from_user.id
    data = user_states[user_id]
    amount = data["amount"]
    wallet = data["wallet"]
    
    if call.data == "method_moment":
        # Отправляем реквизиты
        if os.path.exists(PAYMENT_FILE):
            with open(PAYMENT_FILE) as f:
                payment_text = f.read()
        else:
            payment_text = "Реквизиты: Сбербанк 1234..."
        
        bot.send_message(call.message.chat.id, payment_text)
        
        # Отправляем уведомление в группу
        bot.send_message(
            GROUP_ID,
            f"🚨 Новый заказ:\nID: {user_id}\nUsername: @{call.from_user.username}\nСумма: {amount} BTC\nКошелек: {wallet}\nСпособ: моментально"
        )
    else:
        # Отправляем сообщение о заявке
        bot.send_message(
            call.message.chat.id,
            "Ваша заявка уже обслуживается, для получения реквизитов оплаты свяжитесь с саппортом - @Aboba_Exchange"
        )
        
        # Отправляем уведомление в группу
        bot.send_message(
            GROUP_ID,
            f"📝 Заявка на ожидание:\nID: {user_id}\nUsername: @{call.from_user.username}\nСумма: {amount} BTC\nКошелек: {wallet}"
        )
    
    # Сбрасываем состояние
    del user_states[user_id]

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def show_referral_info(call):
    user_id = str(call.from_user.id)
    referrals = load_json(REFERRALS_FILE, {})
    users = load_json(USERS_FILE, {})
    
    # Кого я привёл
    my_refs = [uid for uid, data in referrals.items() if data.get("ref_by") == user_id]
    
    text = f"🔗 <b>Партнёрская программа:</b>\n\n"
    text += f"Ваша реферальная ссылка:\nhttps://t.me/abobacryptobot?start=ref_{user_id}\n\n"
    text += f"Вы привели: {len(my_refs)} человек\n"
    
    if my_refs:
        text += "\n<b>Ваши рефералы:</b>\n"
        for ref_id in my_refs:
            ref_username = users.get(ref_id, {}).get("username", "unknown")
            text += f"• ID: {ref_id} (@{ref_username})\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("Назад", callback_data="main_menu")
    btn_home = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    markup.add(btn_back, btn_home)
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "support")
def show_support(call):
    markup = types.InlineKeyboardMarkup()
    btn_contact = types.InlineKeyboardButton("Написать менеджеру", url="https://t.me/Aboba_Exchange")
    btn_back = types.InlineKeyboardButton("Назад", callback_data="main_menu")
    btn_home = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    markup.add(btn_contact).add(btn_back, btn_home)
    
    bot.edit_message_text(
        "По всем возникающим вопросам смело обращайтесь в нашу службу заботы",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.message_handler(commands=['enteradmin'])
def enter_admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Введите пароль для входа:")
        user_states[message.from_user.id] = "waiting_password"
    else:
        bot.reply_to(message, "Нет доступа")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_password")
def handle_password(message):
    if message.text == "123":
        admin_sessions.add(message.from_user.id)
        bot.reply_to(message, "Успешно")
        show_admin_menu(message)
    else:
        bot.reply_to(message, "Неверный пароль, попробуйте снова")

def show_admin_menu(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Изменить курс", callback_data="admin_rate")
    btn2 = types.InlineKeyboardButton("Партнёры и рефералы", callback_data="admin_referrals")
    btn3 = types.InlineKeyboardButton("Изменить реквизиты", callback_data="admin_payment")
    btn4 = types.InlineKeyboardButton("Рассылка", callback_data="admin_broadcast")
    btn_back = types.InlineKeyboardButton("Назад", callback_data="main_menu")
    btn_home = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    markup.add(btn1, btn2).add(btn3, btn4).add(btn_back, btn_home)
    
    bot.send_message(message.chat.id, "Меню администратора:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_rate")
def admin_set_rate(call):
    bot.send_message(call.message.chat.id, "Введите новый курс (например, 7150000):")
    user_states[call.from_user.id] = "waiting_new_rate"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_new_rate")
def handle_new_rate(message):
    try:
        new_rate = int(message.text)
        rates = load_json(RATES_FILE, {"BTC": 7000000})
        rates["BTC"] = new_rate
        save_json(RATES_FILE, rates)
        bot.reply_to(message, f"Курс обновлён до {new_rate} ₽")
    except ValueError:
        bot.reply_to(message, "Введите число")

@bot.callback_query_handler(func=lambda call: call.data == "admin_referrals")
def admin_show_referrals(call):
    referrals = load_json(REFERRALS_FILE, {})
    users = load_json(USERS_FILE, {})
    
    text = "<b>Партнёры и рефералы:</b>\n\n"
    partners = {}
    
    # Группируем рефералов по партнёрам
    for user_id, data in referrals.items():
        ref_by = data.get("ref_by")
        if ref_by:
            if ref_by not in partners:
                partners[ref_by] = []
            partners[ref_by].append(user_id)
    
    for partner_id, ref_list in partners.items():
        partner_username = users.get(partner_id, {}).get("username", "unknown")
        text += f"Партнёр: ID {partner_id} (@{partner_username})\n"
        text += f"Привёл: {len(ref_list)} человек\n"
        for ref_id in ref_list:
            ref_username = users.get(ref_id, {}).get("username", "unknown")
            text += f"  - ID: {ref_id} (@{ref_username})\n"
        text += "\n"
    
    if not partners:
        text = "Нет рефералов"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("Назад", callback_data="admin_menu")
    btn_home = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    markup.add(btn_back, btn_home)
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_payment")
def admin_set_payment(call):
    bot.send_message(call.message.chat.id, "Введите новые реквизиты:")
    user_states[call.from_user.id] = "waiting_new_payment"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_new_payment")
def handle_new_payment(message):
    with open(PAYMENT_FILE, "w") as f:
        f.write(message.text)
    bot.reply_to(message, "Реквизиты обновлены!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_start(call):
    bot.send_message(call.message.chat.id, "Введите текст рассылки:")
    user_states[call.from_user.id] = "waiting_broadcast_text"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_broadcast_text")
def handle_broadcast_text(message):
    users = load_json(USERS_FILE, {})
    
    success_count = 0
    for user_id in users.keys():
        try:
            bot.send_message(user_id, message.text)
            success_count += 1
        except:
            pass  # Пользователь заблокировал бота
    
    bot.reply_to(message, f"Рассылка завершена. Отправлено {success_count} пользователям.")

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Мой профиль", callback_data="profile")
    btn2 = types.InlineKeyboardButton("Обмен", callback_data="exchange")
    btn3 = types.InlineKeyboardButton("Партнёрская программа", callback_data="referral")
    btn4 = types.InlineKeyboardButton("Техподдержка", callback_data="support")
    markup.add(btn1, btn2).add(btn3, btn4)
    
    bot.edit_message_text(
        "Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

if __name__ == '__main__':
    bot.infinity_polling()



