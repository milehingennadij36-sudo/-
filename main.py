import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from urllib.parse import urlparse  # Добавлено для работы со ссылками

# --- НАСТРОЙКИ (ВСТАВЬ СВОИ ДАННЫЕ) ---
API_TOKEN = "8806979921:AAG4_e5_gJ3ZEgAiFbSuDax3DpZjRC8fY3U"  # Замени на реальный токен
ADMIN_ID = 8564680065  # Твой Telegram ID (замени)
BOT_USERNAME = "Ciue_hunter_bot"  # Например: "MyShopBot" (без @)

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ХРАНИЛИЩЕ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (простая БД в памяти)
user_stats = {}  # {user_id: {"purchases": 3, "premium": "понимающий" и т.д.}}

# ========== ГЛАВНОЕ МЕНЮ ==========
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="🛒 Покупка проектов", callback_data="menu_projects")],
        [InlineKeyboardButton(text="⚙️ Компиляция JNI", callback_data="menu_compilation")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="menu_profile")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="menu_premium")],
        [InlineKeyboardButton(text="🔗 Ссылка на бота", callback_data="menu_bot_link")]  # Новая кнопка
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== РАЗДЕЛ: ПОКУПКА ПРОЕКТОВ ==========
def get_projects_menu():
    buttons = [
        [InlineKeyboardButton(text="🔥 Мод Блек Раши (26 года)", callback_data="project_blackrush")],
        [InlineKeyboardButton(text="🚀 Лаунчер Блек Раши", callback_data="project_launcher")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_methods(project_name, price, project_type):
    # project_type: "blackrush", "launcher", "ndk25", "ndk24", "ndk16"
    buttons = [
        [InlineKeyboardButton(text="💳 СБП (По номеру телефона)", callback_data=f"pay_sbp_{project_type}")],
        [InlineKeyboardButton(text="💳 Оплата картой", callback_data=f"pay_card_{project_type}")],
        [InlineKeyboardButton(text="✨ Оплата Звёздами Telegram", callback_data=f"pay_stars_{project_type}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_projects")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ССЫЛКА НА БОТА ==========
async def show_bot_link(callback: CallbackQuery):
    bot_link = f"https://t.me/{BOT_USERNAME}"
    text = (f"🔗 <b>Ссылка на бота:</b>\n"
            f"<code>{bot_link}</code>\n\n"
            f"📢 <b>Как поделиться:</b>\n"
            f"• Нажми на ссылку → «Скопировать»\n"
            f"• Отправь друзьям или в чаты\n\n"
            f"🤝 <b>Партнёрская ссылка:</b>\n"
            f"Можешь добавить ?start=ref123 для отслеживания\n\n"
            f"<i>Чем больше пользователей — тем больше продаж!</i>")
    
    # Кнопка с приглашением
    menu_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={bot_link}&text=Купить проект за малую цену!")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=menu_btn, parse_mode="HTML")
    await callback.answer()

# ========== МОД БЛЕК РАШИ ==========
async def show_blackrush_payment(callback: CallbackQuery, method):
    user_id = callback.from_user.id
    price = 250
    product = "Мод Блек Раши-26 года"
    
    if method == "sbp":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"📞 Номер телефона: +79800180927\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "card":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"💳 Карта: 2202 2025 1234 5678\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "stars":
        text = (f"🔹 {product}: (Цена: {price} ⭐)\n"
                f"👤 Админ: @Rider_Mare\n"
                f"💬 После оплаты напишите ему с чеком и вашим ID: {user_id}")
    else:
        return
    
    # Кнопка назад
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_projects")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ========== ЛАУНЧЕР БЛЕК РАШИ ==========
async def show_launcher_payment(callback: CallbackQuery, method):
    user_id = callback.from_user.id
    price = 150
    product = "Лаунчер Блек Раши"
    
    if method == "sbp":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"📞 Номер телефона: +79800180927\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "card":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"💳 Карта: 2202 2025 1234 5678\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "stars":
        text = (f"🔹 {product}: (Цена: {price} ⭐)\n"
                f"👤 Админ: @Rider_Mare\n"
                f"💬 После оплаты напишите ему с чеком и вашим ID: {user_id}")
    else:
        return
    
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_projects")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ========== РАЗДЕЛ: КОМПИЛЯЦИЯ JNI ==========
def get_compilation_menu():
    buttons = [
        [InlineKeyboardButton(text="📦 НДК-25", callback_data="comp_ndk25")],
        [InlineKeyboardButton(text="📦 НДК-24", callback_data="comp_ndk24")],
        [InlineKeyboardButton(text="📦 НДК-16", callback_data="comp_ndk16")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_ndk_payment(callback: CallbackQuery, ndk_version, price, method):
    user_id = callback.from_user.id
    product = f"НДК-{ndk_version}"
    
    if method == "sbp":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"📞 Номер телефона: +79800180927\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "card":
        text = (f"🔹 {product}: (Цена: {price})\n"
                f"💳 Карта: 2202 2025 1234 5678\n"
                f"🏦 Банк: Сбербанк\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"⏳ Ожидайте 2 часа — с вами свяжутся.")
    elif method == "stars":
        text = (f"🔹 {product}: (Цена: {price} ⭐)\n"
                f"👤 Админ: @Rider_Mare\n"
                f"💬 После оплаты напишите ему с чеком и вашим ID: {user_id}")
    else:
        return
    
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_compilation")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ========== КАБИНЕТ ==========
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_stats.get(user_id, {"purchases": 0, "premium": "Нет"})
    
    text = (f"👤 Ваш ID: {user_id}\n"
            f"📦 Куплено проектов: {data['purchases']}\n"
            f"⭐ Премиум статус: {data['premium']}\n"
            f"🕓 Ожидание покупки: 2 часа (стандарт)")
    
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ========== ПРЕМИУМ ==========
def get_premium_menu():
    buttons = [
        [InlineKeyboardButton(text="🏆 Понимающий (350⭐)", callback_data="premium_expert")],
        [InlineKeyboardButton(text="🥈 Средний (250⭐)", callback_data="premium_middle")],
        [InlineKeyboardButton(text="🥉 Начинающий (150⭐)", callback_data="premium_beginner")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_premium_info(callback: CallbackQuery, level):
    if level == "expert":
        text = ("⭐ ПРЕМИУМ «ПОНИМАЮЩИЙ» (350⭐)\n"
                "✅ Покупка проектов за раз: 4\n"
                "✅ Меньше времени ожидания\n"
                "✅ Лаунчер в подарок 🎁")
    elif level == "middle":
        text = ("⭐ ПРЕМИУМ «СРЕДНИЙ» (250⭐)\n"
                "✅ Покупка проектов за раз: 3\n"
                "✅ Чуть меньше времени на сборку\n"
                "✅ Любая компиляция лаунчера за малую цену")
    elif level == "beginner":
        text = ("⭐ ПРЕМИУМ «НАЧИНАЮЩИЙ» (150⭐)\n"
                "✅ Покупка проекта 2 раза\n"
                "✅ Консультация у специалистов\n"
                "✅ 1 компиляция лаунчера за 20⭐")
    else:
        return
    
    text += "\n\n💬 Для покупки пиши @Rider_Mare"
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_premium")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Тут ты можешь купить свой проект за маленькую цену.\nВыбери действие в меню:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Главное меню. Выбери действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# --- Ссылка на бота ---
@dp.callback_query(F.data == "menu_bot_link")
async def bot_link_menu(callback: CallbackQuery):
    await show_bot_link(callback)

# --- Навигация проектов ---
@dp.callback_query(F.data == "menu_projects")
async def projects_menu(callback: CallbackQuery):
    await callback.message.edit_text("🛒 Выбери проект для покупки:", reply_markup=get_projects_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_to_projects")
async def back_to_projects(callback: CallbackQuery):
    await callback.message.edit_text("🛒 Выбери проект для покупки:", reply_markup=get_projects_menu())
    await callback.answer()

# Проект Мод
@dp.callback_query(F.data == "project_blackrush")
async def project_blackrush(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔥 Мод Блек Раши-26 года\nЦена: 250\nВыбери способ оплаты:",
        reply_markup=get_payment_methods("Мод Блек Раши", 250, "blackrush")
    )
    await callback.answer()

# Проект Лаунчер
@dp.callback_query(F.data == "project_launcher")
async def project_launcher(callback: CallbackQuery):
    await callback.message.edit_text(
        "🚀 Лаунчер Блек Раши\nЦена: 150\nВыбери способ оплаты:",
        reply_markup=get_payment_methods("Лаунчер Блек Раши", 150, "launcher")
    )
    await callback.answer()

# Оплата для Мода
@dp.callback_query(F.data.startswith("pay_sbp_blackrush"))
async def pay_sbp_blackrush(callback: CallbackQuery):
    await show_blackrush_payment(callback, "sbp")
@dp.callback_query(F.data.startswith("pay_card_blackrush"))
async def pay_card_blackrush(callback: CallbackQuery):
    await show_blackrush_payment(callback, "card")
@dp.callback_query(F.data.startswith("pay_stars_blackrush"))
async def pay_stars_blackrush(callback: CallbackQuery):
    await show_blackrush_payment(callback, "stars")

# Оплата для Лаунчера
@dp.callback_query(F.data.startswith("pay_sbp_launcher"))
async def pay_sbp_launcher(callback: CallbackQuery):
    await show_launcher_payment(callback, "sbp")
@dp.callback_query(F.data.startswith("pay_card_launcher"))
async def pay_card_launcher(callback: CallbackQuery):
    await show_launcher_payment(callback, "card")
@dp.callback_query(F.data.startswith("pay_stars_launcher"))
async def pay_stars_launcher(callback: CallbackQuery):
    await show_launcher_payment(callback, "stars")

# --- Компиляция JNI ---
@dp.callback_query(F.data == "menu_compilation")
async def compilation_menu(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Выбери версию НДК:", reply_markup=get_compilation_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_to_compilation")
async def back_to_compilation(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Выбери версию НДК:", reply_markup=get_compilation_menu())
    await callback.answer()

@dp.callback_query(F.data == "comp_ndk25")
async def comp_ndk25(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 НДК-25\nЦена: 50\nВыбери способ оплаты:",
        reply_markup=get_payment_methods("НДК-25", 50, "ndk25")
    )
@dp.callback_query(F.data == "comp_ndk24")
async def comp_ndk24(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 НДК-24\nЦена: 60\nВыбери способ оплаты:",
        reply_markup=get_payment_methods("НДК-24", 60, "ndk24")
    )
@dp.callback_query(F.data == "comp_ndk16")
async def comp_ndk16(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 НДК-16\nЦена: 40\nВыбери способ оплаты:",
        reply_markup=get_payment_methods("НДК-16", 40, "ndk16")
    )

# Обработка оплаты НДК
@dp.callback_query(F.data.startswith("pay_sbp_ndk25"))
async def pay_ndk25_sbp(callback: CallbackQuery): await show_ndk_payment(callback, "25", 50, "sbp")
@dp.callback_query(F.data.startswith("pay_card_ndk25"))
async def pay_ndk25_card(callback: CallbackQuery): await show_ndk_payment(callback, "25", 50, "card")
@dp.callback_query(F.data.startswith("pay_stars_ndk25"))
async def pay_ndk25_stars(callback: CallbackQuery): await show_ndk_payment(callback, "25", 50, "stars")

@dp.callback_query(F.data.startswith("pay_sbp_ndk24"))
async def pay_ndk24_sbp(callback: CallbackQuery): await show_ndk_payment(callback, "24", 60, "sbp")
@dp.callback_query(F.data.startswith("pay_card_ndk24"))
async def pay_ndk24_card(callback: CallbackQuery): await show_ndk_payment(callback, "24", 60, "card")
@dp.callback_query(F.data.startswith("pay_stars_ndk24"))
async def pay_ndk24_stars(callback: CallbackQuery): await show_ndk_payment(callback, "24", 60, "stars")

@dp.callback_query(F.data.startswith("pay_sbp_ndk16"))
async def pay_ndk16_sbp(callback: CallbackQuery): await show_ndk_payment(callback, "16", 40, "sbp")
@dp.callback_query(F.data.startswith("pay_card_ndk16"))
async def pay_ndk16_card(callback: CallbackQuery): await show_ndk_payment(callback, "16", 40, "card")
@dp.callback_query(F.data.startswith("pay_stars_ndk16"))
async def pay_ndk16_stars(callback: CallbackQuery): await show_ndk_payment(callback, "16", 40, "stars")

# --- Кабинет ---
@dp.callback_query(F.data == "menu_profile")
async def profile_menu(callback: CallbackQuery):
    await show_profile(callback)
    await callback.answer()

# --- Премиум ---
@dp.callback_query(F.data == "menu_premium")
async def premium_menu(callback: CallbackQuery):
    await callback.message.edit_text("⭐ Выбери уровень премиума:", reply_markup=get_premium_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_to_premium")
async def back_to_premium(callback: CallbackQuery):
    await callback.message.edit_text("⭐ Выбери уровень премиума:", reply_markup=get_premium_menu())
    await callback.answer()

@dp.callback_query(F.data == "premium_expert")
async def premium_expert(callback: CallbackQuery):
    await show_premium_info(callback, "expert")
@dp.callback_query(F.data == "premium_middle")
async def premium_middle(callback: CallbackQuery):
    await show_premium_info(callback, "middle")
@dp.callback_query(F.data == "premium_beginner")
async def premium_beginner(callback: CallbackQuery):
    await show_premium_info(callback, "beginner")

# ========== ЗАПУСК ==========
async def main():
    print("Бот запущен!")
    print(f"Ссылка на бота: https://pokupka-proektov-b6mz.onrender.com{BOT_USERNAME}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
