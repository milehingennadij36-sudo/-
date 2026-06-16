import os
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

# Настройки
BOT_TOKEN = os.getenv('8668731322:AAGqKqZYcC19wqpk8LA6s6_1TxxmPvJPICY')
PORT = int(os.getenv('PORT', 8080))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

# Реквизиты
PHONE = '+79800180927'
BANK = 'Сбер банк'
STARS_ID = 'Rider_Mare'
WAIT_MSG = 'ожидайте 2 часа и с вами свяжутся'

# Товары
ITEMS = {
    'mod_26': {'name': 'Мод Блек Раши-26 года', 'price': 250},
    'launcher': {'name': 'Лаунчер Блек Раши', 'price': 150},
    'ndk_26': {'name': 'НДК-26', 'price': 50},
    'ndk_24': {'name': 'НДК-24', 'price': 60},
    'ndk_16': {'name': 'НДК-16', 'price': 40},
}

PREMIUM = {
    'understanding': {'name': 'Премка понимающий', 'price': 350},
    'medium': {'name': 'Премка средний', 'price': 250},
    'beginner': {'name': 'Премка начинающий', 'price': 150},
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# База данных
DB_NAME = 'bot.db'

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                purchases_count INTEGER DEFAULT 0,
                premium_status TEXT DEFAULT 'none',
                current_order TEXT DEFAULT 'Нет активных заказов',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def get_or_create_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        await db.commit()
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def add_purchase(user_id: int, item_name: str, price: int, payment_method: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'UPDATE users SET purchases_count = purchases_count + 1, current_order = ? WHERE user_id = ?',
            (f'{item_name} ({payment_method})', user_id)
        )
        await db.commit()

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT username, purchases_count, current_order, premium_status FROM users WHERE user_id = ?',
            (user_id,)
        )
        return await cursor.fetchone()

# Клавиатуры
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='💼 Покупка проектов', callback_data='menu_projects'))
    builder.row(InlineKeyboardButton(text='⚙️ Компиляция JNI', callback_data='menu_jni'))
    builder.row(InlineKeyboardButton(text='👤 Кабинет', callback_data='menu_cabinet'))
    builder.row(InlineKeyboardButton(text='💎 Премиум', callback_data='menu_premium'))
    return builder.as_markup()

def projects_menu():
    builder = InlineKeyboardBuilder()    builder.row(InlineKeyboardButton(text='🎮 Мод Блек Раши-26 года', callback_data='item_mod_26'))
    builder.row(InlineKeyboardButton(text='🚀 Лаунчер Блек Раши', callback_data='item_launcher'))
    builder.row(InlineKeyboardButton(text='🔙 Назад', callback_data='main_menu'))
    return builder.as_markup()

def jni_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=' НДК-26', callback_data='item_ndk_26'))
    builder.row(InlineKeyboardButton(text='📦 НДК-24', callback_data='item_ndk_24'))
    builder.row(InlineKeyboardButton(text=' НДК-16', callback_data='item_ndk_16'))
    builder.row(InlineKeyboardButton(text='🔙 Назад', callback_data='main_menu'))
    return builder.as_markup()

def payment_menu(item_code: str, back_callback: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='💳 СБП', callback_data=f'pay_sbp_{item_code}'))
    builder.row(InlineKeyboardButton(text='🏦 Карта', callback_data=f'pay_card_{item_code}'))
    builder.row(InlineKeyboardButton(text='⭐ Звёзды', callback_data=f'pay_stars_{item_code}'))
    builder.row(InlineKeyboardButton(text='🔙 Назад', callback_data=back_callback))
    return builder.as_markup()

def premium_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='👑 Премка понимающий (350⭐)', callback_data='prem_understanding'))
    builder.row(InlineKeyboardButton(text='🥈 Премка средний (250⭐)', callback_data='prem_medium'))
    builder.row(InlineKeyboardButton(text='🥉 Премка начинающий (150⭐)', callback_data='prem_beginner'))
    builder.row(InlineKeyboardButton(text='🔙 Назад', callback_data='main_menu'))
    return builder.as_markup()

def back_to_main():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='🔙 В главное меню', callback_data='main_menu'))
    return builder.as_markup()

# Обработчики
@router.message(CommandStart())
async def cmd_start(message: Message):
    await init_db()
    await get_or_create_user(
        message.from_user.id,
        message.from_user.username or 'Без имени',
        message.from_user.first_name
    )
    text = f"👋 Привет, {message.from_user.first_name}!\n\nТут ты можешь купить свой проект за маленькую цену."
    await message.answer(text, reply_markup=main_menu())

@router.callback_query(F.data == 'main_menu')
async def cb_main_menu(call: CallbackQuery):
    await call.message.edit_text("📌 Главное меню:", reply_markup=main_menu())
@router.callback_query(F.data == 'menu_projects')
async def cb_projects(call: CallbackQuery):
    await call.message.edit_text("🎮 Выберите проект:", reply_markup=projects_menu())

@router.callback_query(F.data == 'menu_jni')
async def cb_jni(call: CallbackQuery):
    await call.message.edit_text("️ Выберите версию JNI:", reply_markup=jni_menu())

@router.callback_query(F.data == 'menu_cabinet')
async def cb_cabinet(call: CallbackQuery):
    stats = await get_user_stats(call.from_user.id)
    if stats:
        username, purchases, current_order, premium = stats
        text = (
            f"👤 **Ваш Кабинет**\n\n"
            f"1. Имя: {username} (ID: {call.from_user.id})\n"
            f"2. Покупок: {purchases}\n"
            f"3. Текущий заказ: {current_order}\n"
            f"4. Премиум: {premium}"
        )
        await call.message.edit_text(text, reply_markup=back_to_main(), parse_mode='Markdown')

@router.callback_query(F.data == 'menu_premium')
async def cb_premium(call: CallbackQuery):
    await call.message.edit_text("💎 Выберите уровень премиума:", reply_markup=premium_menu())

@router.callback_query(F.data == 'item_mod_26')
async def cb_mod_26(call: CallbackQuery):
    item = ITEMS['mod_26']
    text = f" {item['name']}\n💰 Цена: {item['price']}₽\n\nВыберите способ оплаты:"
    await call.message.edit_text(text, reply_markup=payment_menu('mod_26', 'menu_projects'))

@router.callback_query(F.data == 'item_launcher')
async def cb_launcher(call: CallbackQuery):
    item = ITEMS['launcher']
    text = f"🚀 {item['name']}\n💰 Цена: {item['price']}₽\n\nВыберите способ оплаты:"
    await call.message.edit_text(text, reply_markup=payment_menu('launcher', 'menu_projects'))

@router.callback_query(F.data == 'item_ndk_26')
async def cb_ndk_26(call: CallbackQuery):
    item = ITEMS['ndk_26']
    text = f"📦 {item['name']}\n💰 Цена: {item['price']}₽\n\nВыберите способ оплаты:"
    await call.message.edit_text(text, reply_markup=payment_menu('ndk_26', 'menu_jni'))

@router.callback_query(F.data == 'item_ndk_24')
async def cb_ndk_24(call: CallbackQuery):
    item = ITEMS['ndk_24']
    text = f"📦 {item['name']}\n💰 Цена: {item['price']}₽\n\nВыберите способ оплаты:"
    await call.message.edit_text(text, reply_markup=payment_menu('ndk_24', 'menu_jni'))
@router.callback_query(F.data == 'item_ndk_16')
async def cb_ndk_16(call: CallbackQuery):
    item = ITEMS['ndk_16']
    text = f"📦 {item['name']}\n💰 Цена: {item['price']}₽\n\nВыберите способ оплаты:"
    await call.message.edit_text(text, reply_markup=payment_menu('ndk_16', 'menu_jni'))

@router.callback_query(F.data.startswith('pay_sbp_'))
async def cb_pay_sbp(call: CallbackQuery):
    item_code = call.data.split('_')[-1]
    item = ITEMS[item_code]
    await add_purchase(call.from_user.id, item['name'], item['price'], 'СБП')
    
    text = (
        f"1. {item['name']} (цена: {item['price']})\n"
        f"2. Номер телефона: {PHONE}\n"
        f"3. Банк: {BANK}\n"
        f"4. Ваш айди: {call.from_user.id}\n"
        f"5. {WAIT_MSG}"
    )
    await call.message.edit_text(text, reply_markup=back_to_main())

@router.callback_query(F.data.startswith('pay_card_'))
async def cb_pay_card(call: CallbackQuery):
    item_code = call.data.split('_')[-1]
    item = ITEMS[item_code]
    await add_purchase(call.from_user.id, item['name'], item['price'], 'Карта')
    
    text = (
        f"1. {item['name']} (цена: {item['price']})\n"
        f"2. Номер телефона: {PHONE}\n"
        f"3. Банк: {BANK}\n"
        f"4. Ваш айди: {call.from_user.id}\n"
        f"5. {WAIT_MSG}"
    )
    await call.message.edit_text(text, reply_markup=back_to_main())

@router.callback_query(F.data.startswith('pay_stars_'))
async def cb_pay_stars(call: CallbackQuery):
    item_code = call.data.split('_')[-1]
    item = ITEMS[item_code]
    await add_purchase(call.from_user.id, item['name'], item['price'], 'Звёзды')
    
    text = (
        f"1. {item['name']} (цена: {item['price']})\n"
        f"2. Ади: {STARS_ID}"
    )
    await call.message.edit_text(text, reply_markup=back_to_main())

@router.callback_query(F.data == 'prem_understanding')
async def cb_prem_understanding(call: CallbackQuery):    text = (
        "👑 **Премка понимающий (350⭐)**\n\n"
        "1. Покупка проектов за раз: 4\n"
        "2. Меньше времени ждать\n"
        "3. Лаунчер в подарок "
    )
    await call.message.edit_text(text, reply_markup=back_to_main(), parse_mode='Markdown')

@router.callback_query(F.data == 'prem_medium')
async def cb_prem_medium(call: CallbackQuery):
    text = (
        "🥈 **Премка средний (250⭐)**\n\n"
        "1. Покупать проекты 3 штуки за раз\n"
        "2. Чуть меньше даётся время на сборку\n"
        "3. Даётся любая компиляция лаунчера за малую цену"
    )
    await call.message.edit_text(text, reply_markup=back_to_main(), parse_mode='Markdown')

@router.callback_query(F.data == 'prem_beginner')
async def cb_prem_beginner(call: CallbackQuery):
    text = (
        "🥉 **Премка начинающий (150⭐)**\n\n"
        "1. Покупка проекта 2 раза\n"
        "2. Консультация у специалистов\n"
        "3. 1 коррекция лаунчера за 20 звёзд"
    )
    await call.message.edit_text(text, reply_markup=back_to_main(), parse_mode='Markdown')

# Webhook для Render
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=PORT)
