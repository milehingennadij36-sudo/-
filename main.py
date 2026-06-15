import asyncio
import logging
import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from contextlib import contextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
import os

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("8806979921:AAG4_e5_gJ3ZEgAiFbSuDax3DpZjRC8fY3U", "8806979921:AAG4_e5_gJ3ZEgAiFbSuDax3DpZjRC8fY3U")  # Обязательно через переменную окружения!
REQUIRED_CHANNEL = "@A_ToolsX"  # Канал для подписки
REQUIRED_CHANNEL_ID = os.getenv("CHANNEL_ID", "-1001234567890")  # ID канала
ADMIN_IDS = [int(id) for id in os.getenv("8564680065", "8564680065").split(",")]  # ID админов
ADMIN_USERNAME = "@Rider_Mare"

WEBHOOK_HOST = os.getenv("https://pokupka-proektov-1tzy.onrender.com", "https://pokupka-proektov-1tzy.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== БАЗА ДАННЫХ ==========
DB_PATH = "bot_database.db"

@contextmanager
def get_db():
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка БД: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Инициализация базы данных"""
    with get_db() as db:
        # Пользователи
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                purchases INTEGER DEFAULT 0,
                premium_level TEXT DEFAULT NULL,
                premium_until DATETIME DEFAULT NULL,
                total_spent INTEGER DEFAULT 0,
                joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Покупки
        db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                price INTEGER,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Подписанные пользователи
        db.execute("""
            CREATE TABLE IF NOT EXISTS subscribed_users (
                user_id INTEGER PRIMARY KEY,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Логи действий
        db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Админ-заметки
        db.execute("""
            CREATE TABLE IF NOT EXISTS admin_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("База данных инициализирована")

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С БД ==========
def get_user(user_id: int) -> Optional[Dict]:
    """Получить данные пользователя"""
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(user) if user else None

def create_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Создать нового пользователя"""
    with get_db() as db:
        db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))

def update_user_stats(user_id: int, purchase_amount: int = 0):
    """Обновить статистику пользователя"""
    with get_db() as db:
        db.execute("""
            UPDATE users 
            SET purchases = purchases + 1,
                total_spent = total_spent + ?,
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (purchase_amount, user_id))

def add_purchase(user_id: int, product_name: str, price: int, payment_method: str) -> int:
    """Добавить покупку"""
    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO purchases (user_id, product_name, price, payment_method)
            VALUES (?, ?, ?, ?)
        """, (user_id, product_name, price, payment_method))
        return cursor.lastrowid

def update_purchase_status(purchase_id: int, status: str):
    """Обновить статус покупки"""
    with get_db() as db:
        db.execute("UPDATE purchases SET status = ? WHERE id = ?", (status, purchase_id))

def mark_subscribed(user_id: int):
    """Отметить пользователя как подписанного"""
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO subscribed_users (user_id, checked_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (user_id,))

def is_subscribed_checked(user_id: int) -> bool:
    """Проверить, отмечали ли пользователя"""
    with get_db() as db:
        result = db.execute("SELECT 1 FROM subscribed_users WHERE user_id = ?", (user_id,)).fetchone()
        return result is not None

def add_log(user_id: int, action: str, details: str = ""):
    """Добавить лог"""
    with get_db() as db:
        db.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)", 
                   (user_id, action, details))

def get_statistics() -> Dict:
    """Получить статистику"""
    with get_db() as db:
        total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_purchases = db.execute("SELECT SUM(purchases) FROM users").fetchone()[0] or 0
        total_revenue = db.execute("SELECT SUM(total_spent) FROM users").fetchone()[0] or 0
        pending = db.execute("SELECT COUNT(*) FROM purchases WHERE status = 'pending'").fetchone()[0]
        
        return {
            "total_users": total_users,
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "pending_purchases": pending
        }

def get_user_purchases(user_id: int, limit: int = 5) -> List[Dict]:
    """Получить последние покупки пользователя"""
    with get_db() as db:
        purchases = db.execute("""
            SELECT product_name, price, status, created_at 
            FROM purchases WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(p) for p in purchases]

def set_premium(user_id: int, level: str, days: int = 30):
    """Установить премиум статус"""
    until = (datetime.now() + timedelta(days=days)).isoformat()
    with get_db() as db:
        db.execute("""
            UPDATE users SET premium_level = ?, premium_until = ? WHERE user_id = ?
        """, (level, until, user_id))

# ========== FSM СОСТОЯНИЯ ==========
class OrderState(StatesGroup):
    waiting_for_payment = State()
    waiting_for_premium = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Покупка проектов", callback_data="menu_buy_projects")],
        [InlineKeyboardButton(text="⚙️ Компиляция JNI", callback_data="menu_compilation")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="menu_cabinet")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="menu_premium")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu_help")]
    ])

def payment_methods(product_name: str, price: int):
    """Кнопки оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СБП", callback_data=f"pay_sbp_{product_name}_{price}"),
         InlineKeyboardButton(text="💳 Карта", callback_data=f"pay_card_{product_name}_{price}")],
        [InlineKeyboardButton(text="✨ Telegram Stars", callback_data=f"pay_stars_{product_name}_{price}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_buy_projects")]
    ])

def compilation_menu():
    """Меню компиляции"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 NDK-25 (50 руб)", callback_data="comp_ndk25")],
        [InlineKeyboardButton(text="📦 NDK-24 (60 руб)", callback_data="comp_ndk24")],
        [InlineKeyboardButton(text="📦 NDK-16 (40 руб)", callback_data="comp_ndk16")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def premium_menu():
    """Меню премиум"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Понимающий (350⭐)", callback_data="premium_pro")],
        [InlineKeyboardButton(text="🥈 Средний (250⭐)", callback_data="premium_mid")],
        [InlineKeyboardButton(text="🥉 Начинающий (150⭐)", callback_data="premium_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def projects_menu():
    """Меню проектов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Мод Black Rash 2026 (250 руб)", callback_data="product_mod_black_rash")],
        [InlineKeyboardButton(text="🚀 Лаунчер Black Rash (150 руб)", callback_data="product_launcher")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ])

def back_button():
    """Кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ========== MIDDLEWARE ПРОВЕРКИ ПОДПИСКИ ==========
class SubscriptionMiddleware:
    """Middleware для проверки подписки на канал"""
    
    async def __call__(self, handler, event: types.Update, data: dict):
        user = None
        if event.message and event.message.from_user:
            user = event.message.from_user
        elif event.callback_query and event.callback_query.from_user:
            user = event.callback_query.from_user
        
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        
        # Админы пропускают проверку
        if user_id in ADMIN_IDS:
            return await handler(event, data)
        
        # Проверяем, не проверяли ли уже сегодня
        if is_subscribed_checked(user_id):
            return await handler(event, data)
        
        # Проверяем подписку
        try:
            member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
            if member.status in ['member', 'creator', 'administrator']:
                mark_subscribed(user_id)
                return await handler(event, data)
            else:
                # Не подписан
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Перейти в канал", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}")],
                    [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")]
                ])
                
                msg = f"❌ Для использования бота необходимо подписаться на наш канал:\n\n📢 {REQUIRED_CHANNEL}\n\nПосле подписки нажмите «Проверить подписку»"
                
                if event.message:
                    await event.message.answer(msg, reply_markup=keyboard)
                elif event.callback_query:
                    await event.callback_query.message.answer(msg, reply_markup=keyboard)
                    await event.callback_query.answer()
                return  # Не пропускаем дальше
        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
            return await handler(event, data)

# Регистрируем middleware
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    create_user(user.id, user.username, user.first_name, user.last_name)
    add_log(user.id, "start", "Запуск бота")
    
    await message.answer(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Добро пожаловать в магазин проектов!\n"
        f"Здесь ты можешь:\n"
        f"• 🛒 Купить готовые проекты\n"
        f"• ⚙️ Заказать компиляцию JNI\n"
        f"• ⭐ Приобрести премиум доступ\n\n"
        f"Выбери действие:",
        reply_markup=main_menu()
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    stats = get_statistics()
    
    await message.answer(
        f"📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📦 Всего покупок: {stats['total_purchases']}\n"
        f"💰 Общая выручка: {stats['total_revenue']} руб\n"
        f"⏳ Ожидают подтверждения: {stats['pending_purchases']}\n"
        f"🤖 Бот активен: ✅",
        parse_mode="Markdown"
    )

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❌ Укажите текст для рассылки")
        return
    
    with get_db() as db:
        users = db.execute("SELECT user_id FROM users").fetchall()
    
    sent = 0
    failed = 0
    
    status_msg = await message.answer("📤 Начинаю рассылку...")
    
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 **Анонс:**\n\n{text}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\nОтправлено: {sent}\nНе доставлено: {failed}")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Последние логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="⏳ Ожидают оплаты", callback_data="admin_pending")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
    ])
    
    await message.answer("🔧 **Админ-панель**", reply_markup=keyboard, parse_mode="Markdown")

# ========== ОБРАБОТЧИКИ CALLBACK ==========
@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        if member.status in ['member', 'creator', 'administrator']:
            mark_subscribed(user_id)
            await callback.message.delete()
            await callback.message.answer(
                "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.",
                reply_markup=main_menu()
            )
        else:
            await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("⚠️ Ошибка проверки. Попробуйте позже.", show_alert=True)
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_help")
async def help_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📖 **Помощь**\n\n"
        "**Как купить проект?**\n"
        "1. Выберите «Покупка проектов»\n"
        "2. Выберите нужный проект\n"
        "3. Выберите способ оплаты\n"
        "4. После оплаты нажмите «Я оплатил»\n\n"
        "**Способы оплаты:**\n"
        "• СБП / Карта - перевод на номер +79800180927\n"
        "• Telegram Stars - перевод @Rider_Mare\n\n"
        "**Время обработки:**\n"
        "До 2 часов после подтверждения оплаты\n\n"
        "**Контакты:**\n"
        f"👤 Админ: {ADMIN_USERNAME}\n"
        f"📢 Канал: {REQUIRED_CHANNEL}",
        reply_markup=back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_buy_projects")
async def buy_projects_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 **Выбери проект для покупки:**",
        reply_markup=projects_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "product_mod_black_rash")
async def mod_black_rash(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔫 **Мод Black Rash 2026**\n\n"
        "📋 Описание: Полная версия мода для игры\n"
        "💰 Цена: 250 руб\n"
        "📦 В комплекте: мод, инструкция, поддержка\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_methods("Mod_Black_Rash", 250),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "product_launcher")
async def launcher(callback: CallbackQuery):
    await callback.message.edit_text(
        "🚀 **Лаунчер Black Rash**\n\n"
        "📋 Описание: Стильный лаунчер для игры\n"
        "💰 Цена: 150 руб\n"
        "📦 В комплекте: лаунчер, исходники, поддержка\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_methods("Launcher_Black_Rash", 150),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def handle_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    method = parts[1]
    product_name = "_".join(parts[2:-1])
    price = int(parts[-1])
    
    user_id = callback.from_user.id
    
    # Сохраняем покупку
    purchase_id = add_purchase(user_id, product_name, price, method)
    add_log(user_id, "payment_initiated", f"{product_name}:{price}:{method}")
    
    if method in ["sbp", "card"]:
        text = (
            f"💸 **Оплата через {method.upper()}**\n\n"
            f"📦 Товар: {product_name.replace('_', ' ')}\n"
            f"💰 Сумма: {price} руб\n\n"
            f"**Реквизиты:**\n"
            f"📞 Номер: `+79800180927`\n"
            f"🏦 Банк: Сбербанк\n"
            f"👤 Получатель: Адиль\n\n"
            f"🆔 **Ваш ID:** `{user_id}`\n\n"
            f"⚠️ **Важно:**\n"
            f"• Укажите ID в комментарии к переводу\n"
            f"• После оплаты нажмите «Я оплатил»\n\n"
            f"⏳ Ожидайте до 2 часов"
        )
    else:
        stars_amount = price // 5
        text = (
            f"✨ **Оплата Telegram Stars**\n\n"
            f"📦 Товар: {product_name.replace('_', ' ')}\n"
            f"💰 Сумма: {price} руб → ~{stars_amount} ⭐\n\n"
            f"**Как оплатить:**\n"
            f"1. Переведите звезды {ADMIN_USERNAME}\n"
            f"2. Укажите в комментарии ID: `{user_id}`\n"
            f"3. Нажмите «Я оплатил»\n\n"
            f"👤 Получатель: {ADMIN_USERNAME}"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"confirm_{purchase_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_buy_projects")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_payment(callback: CallbackQuery):
    purchase_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Обновляем статус
    update_purchase_status(purchase_id, "confirmed")
    update_user_stats(user_id)
    add_log(user_id, "payment_confirmed", f"purchase_id:{purchase_id}")
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 **Новая покупка!**\n\n"
                f"👤 Пользователь: @{callback.from_user.username or 'нет'} (ID: {user_id})\n"
                f"🆔 ID покупки: {purchase_id}\n"
                f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await callback.message.edit_text(
        "✅ **Заявка принята!**\n\n"
        "Скоро с вами свяжется менеджер (до 2 часов).\n"
        "Спасибо за покупку! 🙏",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_compilation")
async def compilation_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ **Компиляция JNI**\n\n"
        "Выберите версию NDK для компиляции:",
        reply_markup=compilation_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("comp_"))
async def ndk_selected(callback: CallbackQuery):
    ndk_map = {
        "ndk25": ("NDK-25", 50),
        "ndk24": ("NDK-24", 60),
        "ndk16": ("NDK-16", 40)
    }
    key = callback.data.split("_")[1]
    name, price = ndk_map[key]
    
    await callback.message.edit_text(
        f"🛠 **{name}**\n\n"
        f"💰 Цена: {price} руб\n"
        f"⏱️ Срок: до 48 часов\n\n"
        f"Выберите способ оплаты:",
        reply_markup=payment_methods(name, price),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_cabinet")
async def cabinet(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, callback.from_user.username)
        user = get_user(user_id)
    
    premium_text = user['premium_level'] if user['premium_level'] else "Нет"
    if user['premium_until']:
        until = datetime.fromisoformat(user['premium_until']).strftime('%d.%m.%Y')
        premium_text += f" (до {until})"
    
    purchases = get_user_purchases(user_id, 3)
    purchases_text = ""
    if purchases:
        purchases_text = "\n\n**Последние покупки:**\n"
        for p in purchases:
            status = "✅" if p['status'] == 'confirmed' else "⏳"
            purchases_text += f"{status} {p['product_name']} - {p['price']} руб\n"
    
    await callback.message.edit_text(
        f"👤 **Ваш кабинет**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"📦 Куплено проектов: {user['purchases']}\n"
        f"💰 Потрачено: {user['total_spent']} руб\n"
        f"⭐ Премиум: {premium_text}\n"
        f"📅 Регистрация: {user['joined_date'][:10]}{purchases_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_cabinet")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_premium")
async def premium_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌟 **Премиум доступ**\n\n"
        "Выбери уровень премиум:\n\n"
        "🏆 **Понимающий** — 350⭐\n"
        "• Покупка проектов: до 4 за раз\n"
        "• Меньше времени ожидания\n"
        "• Лаунчер в подарок 🎁\n\n"
        "🥈 **Средний** — 250⭐\n"
        "• Покупка проектов: до 3 за раз\n"
        "• Приоритетная компиляция\n\n"
        "🥉 **Начинающий** — 150⭐\n"
        "• Покупка проектов: до 2 за раз\n"
        "• Консультация специалистов",
        reply_markup=premium_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("premium_"))
async def premium_info(callback: CallbackQuery):
    info = {
        "pro": ("🏆 Понимающий (350⭐)", 
                "**Преимущества:**\n"
                "• ✅ Покупка проектов: до 4 за раз\n"
                "• ✅ Меньше времени ожидания\n"
                "• ✅ Лаунчер в подарок 🎁\n"
                "• ✅ Приоритетная поддержка\n"
                "• ✅ Скидка 20% на все услуги"),
        "mid": ("🥈 Средний (250⭐)", 
                "**Преимущества:**\n"
                "• ✅ Покупка проектов: до 3 за раз\n"
                "• ✅ Приоритетная компиляция\n"
                "• ✅ Скидка 10% на все услуги\n"
                "• ✅ Быстрая поддержка"),
        "start": ("🥉 Начинающий (150⭐)", 
                  "**Преимущества:**\n"
                  "• ✅ Покупка проектов: до 2 за раз\n"
                  "• ✅ Консультация специалистов\n"
                  "• ✅ Базовая поддержка")
    }
    level = callback.data.split("_")[1]
    name, benefits = info[level]
    
    await callback.message.edit_text(
        f"{name}\n\n{benefits}\n\n"
        f"💫 **Как купить премиум:**\n"
        f"1. Переведите звезды {ADMIN_USERNAME}\n"
        f"2. Укажите ваш ID: `{callback.from_user.id}`\n"
        f"3. Напишите {ADMIN_USERNAME} после перевода",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_premium")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 **Главное меню**\n\nВыбери действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== АДМИН-ОБРАБОТЧИКИ ==========
@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    stats = get_statistics()
    
    await callback.message.edit_text(
        f"📊 **Статистика**\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📦 Покупок: {stats['total_purchases']}\n"
        f"💰 Выручка: {stats['total_revenue']} руб\n"
        f"⏳ В ожидании: {stats['pending_purchases']}",
        reply_markup=back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_logs")
async def admin_logs(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    with get_db() as db:
        logs = db.execute("""
            SELECT user_id, action, details, created_at 
            FROM logs ORDER BY created_at DESC LIMIT 10
        """).fetchall()
    
    text = "📝 **Последние логи:**\n\n"
    for log in logs:
        text += f"🕐 {log['created_at'][:16]}\n👤 {log['user_id']}\n📌 {log['action']}\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    with get_db() as db:
        pending = db.execute("""
            SELECT id, user_id, product_name, price, created_at 
            FROM purchases WHERE status = 'pending'
            ORDER BY created_at DESC
        """).fetchall()
    
    if not pending:
        await callback.message.edit_text("✅ Нет ожидающих оплат", reply_markup=back_button())
    else:
        text = "⏳ **Ожидают оплаты:**\n\n"
        for p in pending:
            text += f"🆔 {p['id']} | 👤 {p['user_id']}\n📦 {p['product_name']} - {p['price']} руб\n🕐 {p['created_at'][:16]}\n\n"
        
        await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "📢 **Рассылка**\n\n"
        "Отправьте текст для рассылки командой:\n"
        "`/broadcast Ваше сообщение`",
        reply_markup=back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== WEBHOOK НАСТРОЙКА ==========
async def on_startup(bot: Bot):
    """При запуске бота"""
    init_db()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    
    # Проверяем бота
    me = await bot.get_me()
    logger.info(f"🤖 Бот {me.username} запущен")
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"✅ Бот запущен!\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass

async def on_shutdown(bot: Bot):
    """При выключении бота"""
    await bot.delete_webhook()
    logger.info("🔴 Webhook удалён")

# ========== ЗАПУСК ==========
def main():
    """Главная функция запуска"""
    app = web.Application()
    
    # Настройка webhook обработчика
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Регистрируем обработчики старта и остановки
    app.on_startup.append(lambda _: on_startup(bot))
    app.on_shutdown.append(lambda _: on_shutdown(bot))
    
    # Запуск на порту 8080 (как требуется для Render)
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Запуск сервера на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
