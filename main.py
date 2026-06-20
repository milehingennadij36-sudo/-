import os
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)

# Конфигурация из переменных окружения (для Render)
TOKEN = os.getenv("8668731322:AAGqKqZYcC19wqpk8LA6s6_1TxxmPvJPICY", "8668731322:AAGqKqZYcC19wqpk8LA6s6_1TxxmPvJPICY")
PORT = int(os.getenv("PORT", 8080))

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация простой БД
conn = sqlite3.connect("shop_db.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        purchases_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Нет активных заказов'
    )
""")
conn.commit()

# Функция для работы с БД
def get_or_create_user(user_id):
    cursor.execute("SELECT purchases_count, status FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if not data:
        cursor.execute("INSERT INTO users (user_id, purchases_count, status) VALUES (?, 0, 'Нет активных заказов')", (user_id,))
        conn.commit()
        return 0, 'Нет активных заказов'
    return data

# --- КЛАВИАТУРЫ ---

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📁 Покупка проектов", callback_data="buy_projects")
    builder.button(text="⚙️ Компиляция JNI", callback_data="jni_compile")
    builder.button(text="👤 Кабинет", callback_data="cabinet")
    builder.button(text="💎 Премиум", callback_data="premium")
    builder.adjust(2)
    return builder.as_markup()

def pay_methods_kb(item_id, price):
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 СБП", callback_data=f"pay:sbp:{item_id}:{price}")
    builder.button(text="💳 Карта", callback_data=f"pay:card:{item_id}:{price}")
    builder.button(text="⭐ Звёзды", callback_data=f"pay:stars:{item_id}:{price}")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_or_create_user(message.from_user.id)
    await message.answer(
        "Привет! Тут ты можешь купить свой проект за маленькую цену.",
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data == "main_menu")
async def go_to_main_menu(call: types.CallbackQuery):
    await call.message.edit_text(
        "Главное меню. Выбери интересующий раздел:",
        reply_markup=main_menu_kb()
    )

# Раздел 1: Покупка проектов
@dp.callback_query(F.data == "buy_projects")
async def buy_projects_menu(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text=" Мод Блек Раши-26 года (250₽)", callback_data="item:br26:250")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("Выбери проект для покупки:", reply_markup=builder.as_markup())

# Раздел 2: Компиляция JNI
@dp.callback_query(F.data == "jni_compile")
async def jni_menu(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="НДК-25 (50₽)", callback_data="item:ndk25:50")
    builder.button(text="НДК-24 (60₽)", callback_data="item:ndk24:60")
    builder.button(text="НДК-16 (40₽)", callback_data="item:ndk16:40")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("Выбери версию НДК для компиляции:", reply_markup=builder.as_markup())

# Обработка выбора конкретного товара/услуги -> вывод способов оплаты
@dp.callback_query(F.data.startswith("item:"))
async def choose_pay_method(call: types.CallbackQuery):
    _, item_id, price = call.data.split(":")names = {
        "br26": "Мод Блек Раши-26 года",
        "ndk25": "НДК-25",
        "ndk24": "НДК-24",
        "ndk16": "НДК-16"
    }
    item_name = names.get(item_id, "Товар")
    await call.message.edit_text(
        f"Вы выбрали: {item_name}\nЦена: {price} рублей/звёзд.\n\nВыберите способ оплаты:",
        reply_markup=pay_methods_kb(item_id, price)
    )

# Обработка самих способов оплаты
@dp.callback_query(F.data.startswith("pay:"))
async def process_payment(call: types.CallbackQuery):
    _, method, item_id, price = call.data.split(":")
    
    names = {
        "br26": "Мод Блек Раши-26 года",
        "ndk25": "НДК-25",
        "ndk24": "НДК-24",
        "ndk16": "НДК-16"
    }
    item_name = names.get(item_id, "Товар")
    user_id = call.from_user.id

    # Обновляем статус в БД на "В обработке" для демонстрации работы кабинета
    cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (f"Ожидание проверки ({item_name})", user_id))
    conn.commit()

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В главное меню", callback_data="main_menu")

    if method in ["sbp", "card"]:
        text = (
            f" {item_name} (цена: {price})\n"
            f"Номер телефона: +79800180927\n"
            f"Банк: Сбер банк\n"
            f"Ваш ID: {user_id}\n\n"
            f"Ожидайте 2 часа, с вами свяжутся"
        )
    else: # stars
        text = (
            f" {item_name} (цена: {price})\n"
            f"Ади: Rider_Mare"
        )
        
    await call.message.edit_text(text, reply_markup=builder.as_markup())

# Раздел 3: Кабинет
@dp.callback_query(F.data == "cabinet")
async def cabinet_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    count, status = get_or_create_user(user_id)
    
    text = (
        f"👤 Личный кабинет:\n\n"
        f"1. Ваш ID: {user_id}\n"
        f"2. Сколько раз куплено проектов: {count}\n"
        f"3. Ожидание покупки/компиляции: {status}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="main_menu")
    await call.message.edit_text(text, reply_markup=builder.as_markup())

# Раздел 4: Премиум
@dp.callback_query(F.data == "premium")
async def premium_menu(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Премка понимающий (350 ⭐)", callback_data="prem:easy")
    builder.button(text="💎 Премка средний (250 ⭐)", callback_data="prem:mid")
    builder.button(text="💎 Премка начинающий (150 ⭐)", callback_data="prem:hard")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("Выберите уровень Премиума:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("prem:"))
async def prem_info(call: types.CallbackQuery):
    prem_type = call.data.split(":")[1]
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="premium")
    
    if prem_type == "easy":
        text = (
            "💎 Премка понимающий (цена: 350 звёзд)\n\n"
            "Даёт:\n"
            "1. Покупка проектов за раз: 4\n"
            "2. Меньше времени ждать\n"
            "3. Лаунчер в подарок"
        )
    elif prem_type == "mid":
        text = (
            "💎 Премка средний (цена: 250 звёзд)\n\n"
            "Даёт:\n"
            "1. Покупка проектов 3 штуки за раз\n"
            "2. Чуть меньше времени на сборку\n"
            "3. Любая компиляция лаунчера за малую цену"
        )
    else:
        text = (
            "💎 Премка начинающий (цена: 150 звёзд)\n\n"
            "Даёт:\n"
            "1. Покупка проекта 2 раза\n"
            "2. Консультация у специалистов\n"
            "3. 1 корреляция лаунчера за 20 звёзд"
        )
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER & КРОНА ---

async def handle_root(request):
    """Эндпоинт для Крона и Render Web Service"""
    return web.Response(text="Бот активен и работает!", status=200)async def main():
    # Настройка aiohttp приложения
    app = web.Application()
    app.router.add_get('/', handle_root)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    
    # Запускаем веб-сервер асинхронно
    asyncio.create_task(site.start())
    logging.info(f"Веб-сервер запущен на порту {PORT}")
    
    # Запускаем бота (Polling-режим вполне ок, если веб-сервер просто "держит" порт)
    await dp.start_polling(bot)

if name == 'main':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
