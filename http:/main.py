import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ========== НАСТРОЙКИ ==========
TOKEN = "8806979921:AAG4_e5_gJ3ZEgAiFbSuDax3DpZjRC8fY3U"  # Замени на токен от @BotFather
bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных (простая память, при перезапуске всё сотрётся)
user_stats = {}  # {user_id: {"purchases": 0, "premium": None}}

# Webhook настройки
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://твой-бот.onrender.com")  # URL твоего Render приложения
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ========== FSM для состояний ==========
class OrderState(StatesGroup):
    waiting_for_payment = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Покупка проектов", callback_data="menu_buy_projects")],
        [InlineKeyboardButton(text="⚙️ Компиляция JNI", callback_data="menu_compilation")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="menu_cabinet")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="menu_premium")]
    ])

def payment_methods(product_name, price):
    """Кнопки оплаты: СБП, Карта, Звёзды"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СБП", callback_data=f"pay_sbp_{product_name}_{price}"),
         InlineKeyboardButton(text="💳 Карта", callback_data=f"pay_card_{product_name}_{price}")],
        [InlineKeyboardButton(text="✨ Звёзды (Telegram Stars)", callback_data=f"pay_stars_{product_name}_{price}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_buy_projects")]
    ])

def compilation_menu():
    """Меню компиляции JNI"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 НДК-25 (50 руб)", callback_data="comp_ndk25")],
        [InlineKeyboardButton(text="📦 НДК-24 (60 руб)", callback_data="comp_ndk24")],
        [InlineKeyboardButton(text="📦 НДК-16 (40 руб)", callback_data="comp_ndk16")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def premium_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Премка понимающий (350⭐)", callback_data="premium_pro")],
        [InlineKeyboardButton(text="🥈 Премка средний (250⭐)", callback_data="premium_mid")],
        [InlineKeyboardButton(text="🥉 Премка начинающий (150⭐)", callback_data="premium_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_stats:
        user_stats[user_id] = {"purchases": 0, "premium": None}
    await message.answer(
        "Привет! 👋 Тут ты можешь купить свой проект за маленькую цену.\n\nВыбери действие:",
        reply_markup=main_menu()
    )

# Главное меню: Покупка проектов
@dp.callback_query(lambda c: c.data == "menu_buy_projects")
async def buy_projects_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎮 Выбери проект для покупки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔫 Мод Блек Раши-26 года (250 руб)", callback_data="product_mod_black_rash")],
            [InlineKeyboardButton(text="🚀 Лаунчер Блек Раши (150 руб)", callback_data="product_launcher")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "product_mod_black_rash")
async def mod_black_rash(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 Мод Блек Раши-26 года\nЦена: 250 руб\n\nВыбери способ оплаты:",
        reply_markup=payment_methods("Mod_Black_Rash", 250)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "product_launcher")
async def launcher(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🚀 Лаунчер Блек Раши\nЦена: 150 руб\n\nВыбери способ оплаты:",
        reply_markup=payment_methods("Launcher_Black_Rash", 150)
    )
    await callback.answer()

# Обработка способов оплаты
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def handle_payment(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    method = parts[1]  # sbp, card, stars
    product_name = parts[2] + ("_" + parts[3] if len(parts) > 3 else "")
    price = int(parts[-1])
    
    user_id = callback.from_user.id
    username = callback.from_user.username or "без юзернейма"
    
    if method == "sbp" or method == "card":
        text = (f"💸 Оплата через {method.upper()}:\n\n"
                f"📦 {product_name.replace('_', ' ')}: {price} руб\n"
                f"📞 Номер телефона: +79800180927\n"
                f"🏦 Банк: Сбер банк\n"
                f"🆔 Ваш ID: {user_id}\n\n"
                f"⏳ Ожидайте 2 часа, с вами свяжутся.\n"
                f"📌 После оплаты отправьте чек сюда.")
    else:  # stars
        text = (f"✨ Оплата Звёздами Telegram:\n\n"
                f"📦 {product_name.replace('_', ' ')}: {price} руб → {price//5} звёзд (примерно)\n"
                f"👤 Ади (куда переводить): @Rider_Mare\n\n"
                f"⭐ После перевода звёзд нажмите «Подтвердить».")
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"confirm_{product_name}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_buy_projects")]
    ]))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_stats[user_id]["purchases"] += 1
    await callback.message.edit_text(
        "✅ Заявка принята!\nСкоро с вами свяжется менеджер (до 2 часов).\nСпасибо за покупку!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

# Компиляция JNI
@dp.callback_query(lambda c: c.data == "menu_compilation")
async def compilation(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Выбери версию NDK для компиляции:",
        reply_markup=compilation_menu()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("comp_"))
async def ndk_selected(callback: types.CallbackQuery):
    ndk_map = {"ndk25": ("НДК-25", 50), "ndk24": ("НДК-24", 60), "ndk16": ("НДК-16", 40)}
    key = callback.data.split("_")[1]  # ndk25 / ndk24 / ndk16
    name, price = ndk_map[key]
    await callback.message.edit_text(
        f"🛠 {name}\nЦена: {price} руб\n\nСпособы оплаты:",
        reply_markup=payment_methods(name, price)
    )
    await callback.answer()

# Кабинет
@dp.callback_query(lambda c: c.data == "menu_cabinet")
async def cabinet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stats = user_stats.get(user_id, {"purchases": 0, "premium": None})
    premium_text = stats["premium"] if stats["premium"] else "Нет"
    await callback.message.edit_text(
        f"👤 Ваш кабинет:\n\n"
        f"🆔 ID: {user_id}\n"
        f"📦 Куплено проектов: {stats['purchases']} раз\n"
        f"⭐ Премиум: {premium_text}\n"
        f"⏳ Ожидание покупки/компиляции: Нет активных",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

# Премиум
@dp.callback_query(lambda c: c.data == "menu_premium")
async def premium(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌟 Выбери уровень премиум:\n\n"
        "🏆 Понимающий — 350⭐\n🥈 Средний — 250⭐\n🥉 Начинающий — 150⭐",
        reply_markup=premium_menu()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("premium_"))
async def premium_info(callback: types.CallbackQuery):
    info = {
        "pro": ("🏆 Премка понимающий (350⭐)", 
                "• Покупка проектов за раз: 4\n• Меньше времени ждать\n• Лаунчер в подарок 🎁"),
        "mid": ("🥈 Премка средний (250⭐)", 
                "• Покупка проектов 3 штуки за раз\n• Чуть меньше времени на сборку\n• Любая компиляция лаунчера за малую цену"),
        "start": ("🥉 Премка начинающий (150⭐)", 
                  "• Покупка проекта 2 раза\n• Консультация у специалистов\n• 1 корреляция лаунчера за 20 звёзд")
    }
    level = callback.data.split("_")[1]
    name, benefits = info[level]
    await callback.message.edit_text(
        f"{name}\n\nДаёт:\n{benefits}\n\nОплата: переводом звёзд @Rider_Mare",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Купить премиум", callback_data=f"buy_premium_{level}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_premium")]
        ])
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_premium_"))
async def buy_premium(callback: types.CallbackQuery):
    level = callback.data.split("_")[2]
    await callback.message.edit_text(
        "✨ Отправь скриншот оплаты звёздами на @Rider_Mare\nИ напиши сюда «Готово».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

# Назад в главное меню
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu()
    )
    await callback.answer()

# ========== НАСТРОЙКА WEBHOOK ==========
async def on_startup(bot: Bot):
    """При запуске устанавливаем webhook"""
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    """При выключении удаляем webhook"""
    await bot.delete_webhook()
    logging.info("Webhook удалён")

# ========== ЗАПУСК ==========
def main():
    # Запуск веб-приложения
    app = web.Application()
    
    # Настройка webhook обработчика
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Установка обработчиков старта и остановки
    app.on_startup.append(lambda _: on_startup(bot))
    app.on_shutdown.append(lambda _: on_shutdown(bot))
    
    # Запуск приложения на порту 8080
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Запуск сервера на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
