import telebot
from telebot import types
import os
import threading
from flask import Flask

# --- НАСТРОЙКИ ---
API_TOKEN = '8668731322:AAGqKqZYcC19wqpk8LA6s6_1TxxmPvJPICY' # Вставь сюда токен
bot = telebot.TeleBot(API_TOKEN)

# Простая "база данных" в памяти (сбрасывается при перезапуске бота)
users_data = {} 

# --- ФУНКЦИИ ДЛЯ КАБИНЕТА ---
def get_user_data(user_id):
    if user_id not in users_data:
        users_data[user_id] = {'name': user_id, 'count': 0, 'status': 'Нет активных заказов'}
    return users_data[user_id]

def add_purchase(user_id):
    data = get_user_data(user_id)
    data['count'] += 1
    data['status'] = 'Ожидание (2 часа)'

# --- КЛАВИАТУРЫ ---

# Главное меню
def main_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🛒 Покупка проектов", callback_data='buy_projects')
    btn2 = types.InlineKeyboardButton("🔨 Компиляция JNI", callback_data='jni_compilation')
    btn3 = types.InlineKeyboardButton("👤 Кабинет", callback_data='cabinet')
    btn4 = types.InlineKeyboardButton("💎 Премиум", callback_data='premium')
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# Меню покупки проектов
def buy_projects_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("Мод Блек Раши-26 года", callback_data='mod_black_russia')
    btn2 = types.InlineKeyboardButton("Лаунчер Блек Раши", callback_data='launcher_black_russia')
    markup.add(btn1, btn2)
    return markup

# Меню JNI
def jni_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("НДК-25", callback_data='ndk_25')
    btn2 = types.InlineKeyboardButton("НДК-24", callback_data='ndk_24')
    btn3 = types.InlineKeyboardButton("НДК-16", callback_data='ndk_16')    markup.add(btn1, btn2, btn3)
    return markup

# Меню оплаты (общее)
def payment_markup(callback_prefix):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("СБП", callback_data=f'{callback_prefix}_sbp')
    btn2 = types.InlineKeyboardButton("Карта", callback_data=f'{callback_prefix}_card')
    btn3 = types.InlineKeyboardButton("Звёзды", callback_data=f'{callback_prefix}_stars')
    markup.add(btn1, btn2, btn3)
    return markup

# Меню премиума
def premium_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("Премиум Понимающий (350★)", callback_data='prem_ponimayushiy')
    btn2 = types.InlineKeyboardButton("Премиум Средний (250★)", callback_data='prem_sredniy')
    btn3 = types.InlineKeyboardButton("Премиум Начинающий (150★)", callback_data='prem_nachinayushiy')
    markup.add(btn1, btn2, btn3)
    return markup

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = main_menu_markup()
    bot.reply_to(message, "Привет! Тут ты можешь купить свой проект за маленькую цену.", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.lower() == 'меню' or message.text.lower() == 'menu':
        markup = main_menu_markup()
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

# --- ОБРАБОТЧИКИ КНОПОК (CALLBACK) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    chat_id = call.message.chat.id
    
    # ГЛАВНОЕ МЕНЮ
    if call.data == 'buy_projects':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите проект:", reply_markup=buy_projects_markup())
    
    elif call.data == 'jni_compilation':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите NDK для компиляции:", reply_markup=jni_menu_markup())
        
    elif call.data == 'cabinet':
        data = get_user_data(chat_id)
        text = (f"👤 *Кабинет*\n\n"                f"Ваш ID: `{data['name']}`\n"
                f"Куплено проектов: `{data['count']}`\n"
                f"Статус: {data['status']}")
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, parse_mode='Markdown')
        
    elif call.data == 'premium':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите тариф премиума:", reply_markup=premium_markup())

    # ПОКУПКА ПРОЕКТОВ
    elif call.data == 'mod_black_russia':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Мод Блек Раши-26 года. Выберите способ оплаты:", reply_markup=payment_markup('mod_black'))
        
    elif call.data == 'launcher_black_russia':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Лаунчер Блек Раши. Выберите способ оплаты:", reply_markup=payment_markup('launch_black'))

    # JNI КОМПИЛЯЦИЯ
    elif call.data == 'ndk_25':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="НДК-25 (Цена: 50). Выберите оплату:", reply_markup=payment_markup('ndk25'))
    elif call.data == 'ndk_24':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="НДК-24 (Цена: 60). Выберите оплату:", reply_markup=payment_markup('ndk24'))
    elif call.data == 'ndk_16':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="НДК-16 (Цена: 40). Выберите оплату:", reply_markup=payment_markup('ndk16'))

    # ПРЕМИУМ ОПИСАНИЕ
    elif call.data == 'prem_ponimayushiy':
        text = ("👑 *Премиум Понимающий* (350 звёзд)\n\n"
                "Дает:\n"
                "1. Покупка проектов за раз 4\n"
                "2. Меньше времени ждать\n"
                "3. Лаунчер в подарок 🎁")
        bot.send_message(chat_id, text, parse_mode='Markdown')
        # Возвращаем в меню премиума
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите тариф премиума:", reply_markup=premium_markup())

    elif call.data == 'prem_sredniy':
        text = ("👑 *Премиум Средний* (250 звёзд)\n\n"
                "Дает:\n"
                "1. Покупать проекты 3 штуки за раз\n"
                "2. Чуть меньше ждать на сборку\n"
                "3. Любая компиляция лаунчера за малую цену")
        bot.send_message(chat_id, text, parse_mode='Markdown')
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите тариф премиума:", reply_markup=premium_markup())

    elif call.data == 'prem_nachinayushiy':
        text = ("👑 *Премиум Начинающий* (150 звёзд)\n\n"
                "Дает:\n"
                "1. Покупка проекта 2 раза\n"
                "2. Консультация у специалистов\n"
                "3. 1 компиляция лаунчера за 20 звёзд")
        bot.send_message(chat_id, text, parse_mode='Markdown')        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите тариф премиума:", reply_markup=premium_markup())

    # ОПЛАТА (СБП, КАРТА, ЗВЕЗДЫ)
    # Обработка СБП и Карты (текст почти одинаковый, меняем только название товара)
    elif '_sbp' in call.data or '_card' in call.data:
        # Определяем, что покупали
        item_name = ""
        price = ""
        
        if 'mod_black' in call.data:
            item_name = "Мод Блек Раши-26 года"
            price = "250"
        elif 'launch_black' in call.data:
            item_name = "Лаунчер Блек Раши"
            price = "150"
        elif 'ndk25' in call.data:
            item_name = "НДК-25"
            price = "50"
        elif 'ndk24' in call.data:
            item_name = "НДК-24"
            price = "60"
        elif 'ndk16' in call.data:
            item_name = "НДК-16"
            price = "40"
            
        text = (f"💳 *Оплата: {item_name}*\n\n"
                f"Цена: {price} руб.\n"
                f"Номер телефона: +79800180927\n"
                f"Банк: Сбер банк\n"
                f"Ваш ID: {chat_id}\n"
                f"Ожидайте 2 часа и с вами свяжутся.")
        
        bot.send_message(chat_id, text, parse_mode='Markdown')
        add_purchase(chat_id) # Записываем в кабинет
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Главное меню:", reply_markup=main_menu_markup())

    # Обработка Звёзд
    elif '_stars' in call.data:
        text = "💎 Оплата Звёздами.\nВаш ID в Telegram: Rider_Mare\n(Отправьте скриншот перевода или напишите нам)"
        bot.send_message(chat_id, text)
        add_purchase(chat_id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Главное меню:", reply_markup=main_menu_markup())

# --- ЗАПУСК ДЛЯ RENDER (PORT 8080) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке, чтобы держать порт 8080 открытым для Render
    threading.Thread(target=run_flask).start()
    # Запускаем бота
    print("Bot started...")
    bot.polling(none_stop=True)
