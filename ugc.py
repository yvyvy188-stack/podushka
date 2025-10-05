import asyncio
import aiohttp
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict, Any, Tuple, List

API_TOKEN = "7657168761:AAGoq5dUH2jtBMuGO0PRrkuKo5rCopHyWOM"
API_URL = "https://stock-apis.vercel.app/api/plantsvsbrainrots/stocks"
UPDATE_INTERVAL_MINUTES = 5
SETTINGS_FILE = "channels.json"
USERS_FILE = "users.json"
ADMINS_FILE = "admins.json"
REQUIRED_FILE = "required.json"

BOT_PROMO_LINK = "https://t.me/Reports_peImenbot"

ADMINS_DEFAULT = [5194736461]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения {path}: {e}")

user_channels: Dict[str, Any] = load_json(SETTINGS_FILE, {})
user_settings: Dict[str, Any] = load_json(USERS_FILE, {})
ADMINS = load_json(ADMINS_FILE, ADMINS_DEFAULT)
required_channels = load_json(REQUIRED_FILE, [])  # list of channel usernames/links (strings)

def save_settings():
    save_json(SETTINGS_FILE, user_channels)

def save_users():
    save_json(USERS_FILE, user_settings)

def save_admins():
    save_json(ADMINS_FILE, ADMINS)

def save_required():
    save_json(REQUIRED_FILE, required_channels)

# canonical rarities
RARITIES = ["common","rare","epic","legendary","mythic","godly","secret","limited"]

# visible names -> emoji (kept same as у тебя)
PLANT_NAMES = [
    "Cactus Seed",
    "Strawberry Seed",
    "Pumpkin Seed",
    "Sunflower Seed",
    "Dragon Fruit Seed",
    "Eggplant Seed",
    "Watermelon Seed",
    "Grapes Seed",
    "Cocotank Seed",
    "Carnivorous Plant Seed",
    "Mr Carrot Seed",
    "Tomatrio Seed",
    "Mango Seed",
    "Shroombino Seed"
]
PLANTS = {
    "Cactus Seed": "🌵",
    "Strawberry Seed": "🍓",
    "Pumpkin Seed": "🎃",
    "Sunflower Seed": "🌻",
    "Dragon Fruit Seed": "🐉",
    "Eggplant Seed": "🍆",
    "Watermelon Seed": "🍉",
    "Grapes Seed": "🍇",
    "Cocotank Seed": "🥥",
    "Carnivorous Plant Seed": "🪴",
    "Mr Carrot Seed": "🥕",
    "Tomatrio Seed": "🍅",
    "Mango Seed": "🥭",
    "Shroombino Seed": "🍄"
}

GEAR_NAMES = [
    "Water Bucket",
    "Frost Grenade",
    "Banana Gun",
    "Frost Blower",
    "Carrot Launcher"
]
GEAR = {
    "Water Bucket": "🪣",
    "Frost Grenade": "💣❄️",
    "Banana Gun": "🍌🔫",
    "Frost Blower": "🌬️❄️",
    "Carrot Launcher": "🥕🚀"
}

CUSTOM_RARITIES = {
    "Cactus Seed": "Rare",
    "Strawberry Seed": "Rare",
    "Pumpkin Seed": "Epic",
    "Sunflower Seed": "Epic",
    "Dragon Fruit Seed": "Legendary",
    "Eggplant Seed": "Legendary",
    "Watermelon Seed": "Mythic",
    "Grapes Seed": "Mythic",
    "Cocotank Seed": "Godly",
    "Carnivorous Plant Seed": "Godly",
    "Mr Carrot Seed": "Secret",
    "Tomatrio Seed": "Secret",
    "Mango Seed": "Secret",
    "Shroombino Seed": "Secret",
}

CUSTOM_GEAR_RARITIES = {
    "Water Bucket": "Epic",
    "Frost Grenade": "Epic",
    "Banana Gun": "Epic",
    "Frost Blower": "Legendary",
    "Carrot Launcher": "Godly",
}

# --- callback id mapping (short codes to long names) ---
# p1..pn for plants, g1.. for gear, r1.. for rarities
PLANT_CODE_TO_NAME: Dict[str, str] = {}
PLANT_NAME_TO_CODE: Dict[str, str] = {}
for i, name in enumerate(PLANT_NAMES, start=1):
    code = f"p{i}"
    PLANT_CODE_TO_NAME[code] = name
    PLANT_NAME_TO_CODE[name] = code

GEAR_CODE_TO_NAME: Dict[str, str] = {}
GEAR_NAME_TO_CODE: Dict[str, str] = {}
for i, name in enumerate(GEAR_NAMES, start=1):
    code = f"g{i}"
    GEAR_CODE_TO_NAME[code] = name
    GEAR_NAME_TO_CODE[name] = code

RARITY_CODE_TO_NAME: Dict[str, str] = {}
RARITY_NAME_TO_CODE: Dict[str, str] = {}
for i, name in enumerate(RARITIES, start=1):
    code = f"r{i}"
    RARITY_CODE_TO_NAME[code] = name
    RARITY_NAME_TO_CODE[name] = code

pending_actions: Dict[int, str] = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def normalize_channel_link(link: str) -> str:
    link = str(link).strip()
    if not link:
        return ""
    if link.startswith("https://t.me/"):
        return "@" + link.split("/")[-1].strip()
    if link.startswith("http://t.me/"):
        return "@" + link.split("/")[-1].strip()
    if link.startswith("@"):
        return link
    return "@" + link

async def get_stocks():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print("get_stocks status:", resp.status)
    except Exception as e:
        print("get_stocks error:", e)
    return None

async def delete_later(chat_id: int, message_id: int, delay_seconds: int = 300):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def format_stocks(data: dict, settings: dict) -> str | None:
    plant_lines, gear_lines = [], []
    mode = settings.get("mode", "all")
    allowed_rarities = settings.get("rarities", []) or []

    for seed in data.get("seed_stock", []):
        name = seed.get("name", "")
        rarity_raw = seed.get("rarity", "")
        rarity_display = CUSTOM_RARITIES.get(name, rarity_raw.capitalize())
        include = False
        if mode == "all":
            include = True
        else:
            if settings.get("plants") and name in settings.get("plants", []):
                include = True
            if allowed_rarities and rarity_raw.lower() in allowed_rarities:
                include = True
        if include:
            emoji = PLANTS.get(name, "🌱")
            plant_lines.append(f"{emoji} <b>{name}</b> ({rarity_display})\n   📦 В наличии: {seed.get('stock', 0)}\n")

    for g in data.get("gear_stock", []):
        name = g.get("name", "")
        rarity_raw = g.get("rarity", "")
        rarity_display = CUSTOM_GEAR_RARITIES.get(name, rarity_raw.capitalize())
        include = False
        if mode == "all":
            include = True
        else:
            if settings.get("gear") and name in settings.get("gear", []):
                include = True
            if allowed_rarities and rarity_raw.lower() in allowed_rarities:
                include = True
        if include:
            emoji = GEAR.get(name, "🛠")
            gear_lines.append(f"{emoji} <b>{name}</b> ({rarity_display})\n   📦 В наличии: {g.get('stock', 0)}\n")

    if not plant_lines and not gear_lines:
        return None

    text = "━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "📊 <b>Plants vs Brainrots – Stocks</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if plant_lines:
        text += "<b>🌿 Plants</b>\n" + "\n".join(plant_lines) + "\n"
    if gear_lines:
        text += "⚔️ <b>Gear</b>\n" + "\n".join(gear_lines) + "\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "👨‍💻 <a href='https://t.me/PIants_vs_brainr0ts'>Plants vs brainrots</a>"
    return text

async def check_user_subs(user_id: int) -> Tuple[bool, List[str]]:
    not_subscribed = []
    for ch in required_channels:
        ch_norm = normalize_channel_link(ch)
        if not ch_norm:
            continue
        try:
            member = await bot.get_chat_member(ch_norm, user_id)
            if member.status not in ("member", "creator", "administrator"):
                not_subscribed.append(ch_norm)
        except Exception:
            not_subscribed.append(ch_norm)
    return (len(not_subscribed) == 0, not_subscribed)

def build_user_menu(uid: str) -> InlineKeyboardBuilder:
    us = user_settings.setdefault(uid, {
        "receive": False, "mode": "all",
        "plants": [], "gear": [], "rarities": [],
        "autodelete": True, "autodelete_delay": 5
    })
    kb = InlineKeyboardBuilder()
    rcv = "✅ Вкл" if us["receive"] else "❌ Выкл"
    kb.button(text=f"🔔 Получение стоков: {rcv}", callback_data=f"user_toggle:{uid}")
    mode = "Весь" if us["mode"] == "all" else "Фильтр"
    kb.button(text=f"⚙️ Режим: {mode}", callback_data=f"user_mode:{uid}")
    kb.button(text="🌿 Фильтр растений", callback_data=f"user_plants:{uid}")
    kb.button(text="⚔️ Фильтр предметов", callback_data=f"user_gear:{uid}")
    kb.button(text="🎖 Фильтр редкостей", callback_data=f"user_rarity:{uid}")
    ad = "✅ Вкл" if us["autodelete"] else "❌ Выкл"
    kb.button(text=f"⏱ Автоудаление: {ad}", callback_data=f"user_autodel:{uid}")
    kb.button(text="📤 Тест стока", callback_data=f"user_test:{uid}")
    kb.adjust(1)
    return kb

def build_admin_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Управление каналами", callback_data="admin:channels")
    kb.button(text="👤 Личные настройки", callback_data="admin:settings")
    kb.button(text="➕ Добавить админа", callback_data="admin:add_admin")
    kb.button(text="📋 Список админов", callback_data="admin:list_admins")
    kb.button(text="👥 Пользователи", callback_data="admin:users")
    kb.button(text="🔒 Обязательные подписки", callback_data="admin:required")
    kb.adjust(1)
    return kb

# compact helper to safely build .as_markup() and avoid too-long callback_data
def safe_markup(builder: InlineKeyboardBuilder):
    try:
        return builder.as_markup()
    except Exception:
        # fallback: convert to minimal markup
        return types.InlineKeyboardMarkup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    uid_str = str(message.from_user.id)
    if is_admin(message.from_user.id):
        kb = build_admin_menu()
        await message.answer("👑 Панель администратора:", reply_markup=safe_markup(kb))
        return
    user_settings.setdefault(uid_str, {
        "receive": False, "mode": "all",
        "plants": [], "gear": [], "rarities": [],
        "autodelete": True, "autodelete_delay": 5
    })
    ok, not_subs = await check_user_subs(message.from_user.id)
    if not ok:
        kb = InlineKeyboardBuilder()
        for ch in not_subs:
            kb.button(text=f"👉 {ch}", callback_data=f"noop")
        kb.button(text="🔄 Проверить подписку", callback_data=f"checksubs:{uid_str}")
        kb.adjust(1)
        txt = "🚫 Чтобы пользоваться ботом, подпишись на каналы (админ установил обязательные подписки):\n\n"
        txt += "\n".join([f"- https://t.me/{ch.lstrip('@')}" for ch in not_subs])
        await message.answer(txt, reply_markup=safe_markup(kb))
        return
    kb = build_user_menu(uid_str)
    await message.answer("⚙️ Твои настройки:", reply_markup=safe_markup(kb))

@dp.callback_query(lambda c: c.data and c.data.startswith("checksubs:"))
async def cb_checksubs(callback: types.CallbackQuery):
    uid = int(callback.data.split(":",1)[1])
    ok, not_subs = await check_user_subs(uid)
    if ok:
        await callback.message.edit_text("✅ Все подписки в порядке. Возвращаемся к меню.", reply_markup=safe_markup(build_user_menu(str(uid))))
    else:
        kb = InlineKeyboardBuilder()
        for ch in not_subs:
            kb.button(text=f"👉 {ch}", callback_data="noop")
        kb.button(text="🔄 Проверить подписку", callback_data=f"checksubs:{uid}")
        kb.adjust(1)
        txt = "🚫 Всё ещё не подписаны на:\n" + "\n".join([f"- https://t.me/{ch.lstrip('@')}" for ch in not_subs])
        await callback.message.edit_text(txt, reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("user_toggle:"))
async def cb_user_toggle(callback: types.CallbackQuery):
    uid = callback.data.split(":", 1)[1]
    ok, not_subs = await check_user_subs(int(uid))
    if not ok:
        kb = InlineKeyboardBuilder()
        for ch in not_subs:
            kb.button(text=f"👉 {ch}", callback_data="noop")
        kb.button(text="🔄 Проверить подписку", callback_data=f"checksubs:{uid}")
        kb.adjust(1)
        txt = "🚫 Чтобы получать стоки, подпишись на каналы:\n" + "\n".join([f"- https://t.me/{ch.lstrip('@')}" for ch in not_subs])
        await callback.message.answer(txt, reply_markup=safe_markup(kb))
        await callback.answer()
        return
    user_settings[uid]["receive"] = not user_settings[uid].get("receive", False)
    save_users()
    await callback.message.edit_reply_markup(reply_markup=safe_markup(build_user_menu(uid)))
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("user_mode:"))
async def cb_user_mode(callback: types.CallbackQuery):
    uid = callback.data.split(":", 1)[1]
    us = user_settings.setdefault(uid, {
        "receive": False, "mode": "all",
        "plants": [], "gear": [], "rarities": [],
        "autodelete": True, "autodelete_delay": 5
    })
    us["mode"] = "filtered" if us.get("mode","all") == "all" else "all"
    save_users()
    await callback.message.edit_reply_markup(reply_markup=safe_markup(build_user_menu(uid)))
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("user_test:"))
async def cb_user_test(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    data = await get_stocks()
    if not data:
        await callback.message.answer("❌ Ошибка API.")
        await callback.answer()
        return
    text = format_stocks(data, user_settings.get(uid, {}))
    if not text:
        await callback.message.answer("ℹ️ По фильтрам нет позиций.")
        await callback.answer()
        return
    msg = await bot.send_message(int(uid), text, parse_mode="HTML")
    if user_settings.get(uid,{}).get("autodelete", True):
        delay = user_settings.get(uid,{}).get("autodelete_delay", 5) * 60
        asyncio.create_task(delete_later(msg.chat.id, msg.message_id, delay))
    await callback.answer("Отправлено")

# ----- User filter menus (use short callback_data codes) -----

def build_user_plants_keyboard(uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all", "plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    for code, name in PLANT_CODE_TO_NAME.items():
        mark = "✅" if name in us["plants"] else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"utp:{uid}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"user_back:{uid}")
    kb.adjust(1)
    return kb

def build_user_gear_keyboard(uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all", "plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    for code, name in GEAR_CODE_TO_NAME.items():
        mark = "✅" if name in us["gear"] else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"utg:{uid}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"user_back:{uid}")
    kb.adjust(1)
    return kb

def build_user_rarity_keyboard(uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all", "plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    for code, name in RARITY_CODE_TO_NAME.items():
        mark = "✅" if name in us["rarities"] else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"utr:{uid}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"user_back:{uid}")
    kb.adjust(2)
    return kb

@dp.callback_query(lambda c: c.data and c.data.startswith("user_plants:"))
async def cb_user_plants(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    kb = build_user_plants_keyboard(uid)
    # edit current message if possible, otherwise answer new message
    try:
        await callback.message.edit_text("Выбери растения:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("Выбери растения:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("user_gear:"))
async def cb_user_gear(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    kb = build_user_gear_keyboard(uid)
    try:
        await callback.message.edit_text("Выбери предметы:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("Выбери предметы:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("user_rarity:"))
async def cb_user_rarity(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    kb = build_user_rarity_keyboard(uid)
    try:
        await callback.message.edit_text("Выбери редкости:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("Выбери редкости:", reply_markup=safe_markup(kb))
    await callback.answer()

# handlers for short-coded toggles (utp = user toggle plant, utg = gear, utr = rarity)
@dp.callback_query(lambda c: c.data and c.data.startswith("utp:"))
async def cb_user_toggle_plant_short(callback: types.CallbackQuery):
    # format: utp:uid:pc
    try:
        _, uid, code = callback.data.split(":",2)
    except ValueError:
        await callback.answer()
        return
    name = PLANT_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all","plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    if name in us["plants"]:
        us["plants"].remove(name)
    else:
        us["plants"].append(name)
    save_users()
    kb = build_user_plants_keyboard(uid)
    try:
        await callback.message.edit_text("Выбери растения:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("utg:"))
async def cb_user_toggle_gear_short(callback: types.CallbackQuery):
    try:
        _, uid, code = callback.data.split(":",2)
    except ValueError:
        await callback.answer()
        return
    name = GEAR_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all","plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    if name in us["gear"]:
        us["gear"].remove(name)
    else:
        us["gear"].append(name)
    save_users()
    kb = build_user_gear_keyboard(uid)
    try:
        await callback.message.edit_text("Выбери предметы:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("utr:"))
async def cb_user_toggle_rarity_short(callback: types.CallbackQuery):
    try:
        _, uid, code = callback.data.split(":",2)
    except ValueError:
        await callback.answer()
        return
    name = RARITY_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all","plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    if name in us["rarities"]:
        us["rarities"].remove(name)
    else:
        us["rarities"].append(name)
    save_users()
    kb = build_user_rarity_keyboard(uid)
    try:
        await callback.message.edit_text("Выбери редкости:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("user_autodel:"))
async def cb_user_autodel(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all","plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    kb = InlineKeyboardBuilder()
    state = "✅ Вкл" if us["autodelete"] else "❌ Выкл"
    kb.button(text=f"🔄 Автоудаление: {state}", callback_data=f"user_toggle_autodel:{uid}")
    kb.button(text="✍ Ввести время (мин)", callback_data=f"user_set_delay:{uid}")
    kb.button(text="⬅️ Назад", callback_data=f"user_back:{uid}")
    kb.adjust(1)
    try:
        await callback.message.edit_text("Настрой автоудаление личных сообщений:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("Настрой автоудаление личных сообщений:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("user_toggle_autodel:"))
async def cb_user_toggle_autodel(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    us = user_settings.setdefault(uid, {"receive": False, "mode":"all","plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
    us["autodelete"] = not us.get("autodelete", True)
    save_users()
    await callback.answer("Обновлено")
    await cb_user_autodel(callback)

@dp.callback_query(lambda c: c.data and c.data.startswith("user_set_delay:"))
async def cb_user_set_delay(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    pending_actions[callback.from_user.id] = f"user_delay:{uid}"
    try:
        await callback.message.edit_text("Введи время удаления личных сообщений в минутах (целое число).")
    except Exception:
        await callback.message.answer("Введи время удаления личных сообщений в минутах (целое число).")
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("user_back:"))
async def cb_user_back(callback: types.CallbackQuery):
    uid = callback.data.split(":",1)[1]
    try:
        await callback.message.edit_reply_markup(reply_markup=safe_markup(build_user_menu(uid)))
    except Exception:
        await callback.message.answer("Возврат в меню.", reply_markup=safe_markup(build_user_menu(uid)))
    await callback.answer()

@dp.message()
async def handle_pending_inputs(message: types.Message):
    uid = message.from_user.id
    if uid not in pending_actions:
        return
    action = pending_actions.pop(uid)
    if action.startswith("user_delay:"):
        _, target_uid = action.split(":",1)
        try:
            minutes = int(message.text.strip())
            if minutes <= 0:
                await message.answer("Введи положительное число минут.")
                return
            user_settings.setdefault(target_uid, {"receive": False, "mode": "all", "plants": [], "gear": [], "rarities": [], "autodelete": True, "autodelete_delay": 5})
            user_settings[target_uid]["autodelete_delay"] = minutes
            save_users()
            await message.answer(f"✅ Время автоудаления личных сообщений установлено: {minutes} мин")
        except Exception:
            await message.answer("Неверный формат. Введи целое число минут.")
        return
    if action == "add_channel":
        parts = message.text.strip().split()
        try:
            ch_id = int(parts[0])
        except Exception:
            await message.answer("Неверный формат ID канала.")
            return
        required = []
        if len(parts) > 1:
            rest = " ".join(parts[1:]).replace(",", " ").split()
            for r in rest:
                try:
                    required.append(int(r))
                except Exception:
                    pass
        s_uid = str(uid)
        if s_uid not in user_channels:
            user_channels[s_uid] = []
        user_channels[s_uid].append({
            "id": ch_id,
            "mode": "all",
            "plants": [],
            "gear": [],
            "rarities": [],
            "autodelete": True,
            "autodelete_delay": 5,
            "required_subs": required
        })
        save_settings()
        await message.answer(f"✅ Канал {ch_id} добавлен. required_subs: {required}")
        return
    if action.startswith("set_required:"):
        parts = action.split(":")
        ch_id = int(parts[1])
        s_uid = str(message.from_user.id)
        channel = next((c for c in user_channels.get(s_uid, []) if c["id"] == ch_id), None)
        if channel is None:
            await message.answer("Канал не найден.")
            return
        rest = message.text.replace(",", " ").split()
        required = []
        for r in rest:
            try:
                required.append(int(r))
            except Exception:
                pass
        channel["required_subs"] = required
        save_settings()
        await message.answer(f"required_subs для {ch_id} сохранены: {required}")
        return
    if action.startswith("delay:"):
        try:
            parts = action.split(":")
            ch_id = int(parts[1])
            minutes = int(message.text.strip())
            if minutes <= 0:
                await message.answer("Введите положительное число минут.")
                return
            s_uid = str(message.from_user.id)
            channel = next((c for c in user_channels.get(s_uid, []) if c["id"] == ch_id), None)
            if channel:
                channel["autodelete_delay"] = minutes
                save_settings()
                await message.answer(f"✅ Время автоудаления установлено: {minutes} мин")
            else:
                await message.answer("Канал не найден.")
        except Exception:
            await message.answer("Неверный формат. Введите число минут.")
        return
    if action == "set_required_global":
        rest = message.text.replace(",", " ").split()
        new_required = []
        for r in rest:
            try:
                nr = normalize_channel_link(r)
                if nr:
                    new_required.append(nr)
            except Exception:
                pass
        seen = set()
        new_required_clean = []
        for x in new_required:
            if x not in seen:
                seen.add(x)
                new_required_clean.append(x)
        required_channels.clear()
        required_channels.extend(new_required_clean)
        save_required()
        await message.answer(f"✅ Глобальные required_subs установлены: {required_channels}")
        return

# Admin callbacks (some simplified UI improvements)
@dp.callback_query(lambda c: c.data == "admin:channels")
async def admin_channels(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    uid = str(callback.from_user.id)
    channels = user_channels.get(uid, [])
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить канал", callback_data="add_channel")
    if channels:
        for ch in channels:
            kb.button(text=f"⚙️ {ch['id']}", callback_data=f"config:{ch['id']}")
            kb.button(text=f"🗑 Удалить {ch['id']}", callback_data=f"delete:{ch['id']}")
    else:
        kb.button(text="Нет каналов", callback_data="noop")
    kb.button(text="⬅️ Назад", callback_data="admin:main")
    kb.adjust(1)
    try:
        await callback.message.edit_text("📢 Управление каналами:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("📢 Управление каналами:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin:settings")
async def admin_settings(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    uid = str(callback.from_user.id)
    kb = build_user_menu(uid)
    try:
        await callback.message.edit_text("⚙️ Личные настройки администратора:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("⚙️ Личные настройки администратора:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin:add_admin")
async def admin_add_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    try:
        await callback.message.edit_text("Используй команду /addadmin <id> для добавления админа.")
    except Exception:
        await callback.message.answer("Используй команду /addadmin <id> для добавления админа.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin:list_admins")
async def admin_list_admins(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    text = "📋 Список админов:\n" + "\n".join([f"- <code>{a}</code>" for a in ADMINS])
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=safe_markup(build_admin_menu()))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=safe_markup(build_admin_menu()))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin:users")
async def admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    # build list of users: id + username + status
    lines = []
    for uid_str, settings in user_settings.items():
        status = "✅" if settings.get("receive", False) else "❌"
        try:
            # try get username via get_chat; fail silently
            info = await bot.get_chat(int(uid_str))
            uname = f"@{info.username}" if getattr(info, "username", None) else "—"
        except Exception:
            uname = "—"
        lines.append(f"👤 <code>{uid_str}</code> ({uname}) – {status}")
    if not lines:
        text = "Пользователей нет."
    else:
        text = "👥 Пользователи:\n\n" + "\n".join(lines)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=safe_markup(build_admin_menu()))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=safe_markup(build_admin_menu()))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin:required")
async def admin_required(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="✍ Установить/Изменить обязательные подписки", callback_data="set_required_global")
    kb.button(text="🔍 Показать текущие", callback_data="show_required_global")
    kb.button(text="⬅️ Назад", callback_data="admin:main")
    kb.adjust(1)
    try:
        await callback.message.edit_text("🔒 Глобальные обязательные подписки:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.message.answer("🔒 Глобальные обязательные подписки:", reply_markup=safe_markup(kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_required_global")
async def show_required_global(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    if not required_channels:
        txt = "Пока не установлены глобальные обязательные подписки."
    else:
        txt = "Текущие обязательные подписки (usernames/links):\n" + "\n".join(str(x) for x in required_channels)
    try:
        await callback.message.edit_text(txt, reply_markup=safe_markup(build_admin_menu()))
    except Exception:
        await callback.message.answer(txt, reply_markup=safe_markup(build_admin_menu()))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "set_required_global")
async def set_required_global(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    pending_actions[callback.from_user.id] = "set_required_global"
    try:
        await callback.message.answer("Введи список каналов (юзернеймы или ссылки) через пробел или запятую. Примеры:\n@channel1 https://t.me/channel2 channel3")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data == "add_channel")
async def cb_add_channel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    pending_actions[callback.from_user.id] = "add_channel"
    try:
        await callback.message.answer("Введи ID канала (например -1001234567890) и через пробел (опционально) required_subs через запятую или пробел.\nПример:\n-1001234567890 -100111,-100222")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("delete:"))
async def cb_delete_channel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    try:
        ch_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Неверный id")
        return
    uid = str(callback.from_user.id)
    if uid in user_channels:
        user_channels[uid] = [c for c in user_channels[uid] if c["id"] != ch_id]
        save_settings()
    try:
        await callback.message.answer(f"🗑 Канал {ch_id} удалён.")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("config:"))
async def cb_config(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel is None:
        await callback.answer("Канал не найден.")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Весь сток", callback_data=f"all:{ch_id}")
    kb.button(text="🔍 Фильтрованный сток", callback_data=f"filtered:{ch_id}")
    kb.button(text="🎯 Required subs", callback_data=f"set_required:{ch_id}")
    kb.button(text="⏱ Автоудаление", callback_data=f"autodelete:{ch_id}")
    kb.button(text="📤 Тест", callback_data=f"testchannel:{ch_id}")
    kb.button(text="⬅️ Назад", callback_data="admin:channels")
    kb.adjust(1)
    try:
        await callback.message.answer(f"Настройки канала {ch_id}:", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("set_required:"))
async def cb_set_required(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    ch_id = int(callback.data.split(":",1)[1])
    pending_actions[callback.from_user.id] = f"set_required:{ch_id}"
    try:
        await callback.message.answer("Введи список required_subs для этого канала через пробел или запятую (IDs каналов). Пример: -100111 -100222")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("all:"))
async def cb_all(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel:
        channel["mode"] = "all"
        channel["plants"] = []
        channel["gear"] = []
        channel.setdefault("rarities", [])
        channel["rarities"].clear()
        save_settings()
        try:
            await callback.message.answer("📦 Включен полный сток.")
        except Exception:
            pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("filtered:"))
async def cb_filtered(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.")
        return
    ch_id = int(callback.data.split(":",1)[1])
    kb = InlineKeyboardBuilder()
    kb.button(text="🌿 Растения", callback_data=f"plants:{ch_id}")
    kb.button(text="⚔️ Предметы", callback_data=f"gear:{ch_id}")
    kb.button(text="🎖 Редкости", callback_data=f"rarity:{ch_id}")
    kb.button(text="⬅️ Назад", callback_data=f"config:{ch_id}")
    kb.adjust(2)
    try:
        await callback.message.answer("🔍 Настрой фильтр:", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

# Admin filter menus use same short codes but prefixed with 'ap'/'ag'/'ar' (admin plant/gear/rarity)
def build_admin_plants_keyboard(ch_id: int, uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    channel = channel or {"plants": []}
    for code, name in PLANT_CODE_TO_NAME.items():
        mark = "✅" if name in channel.get("plants", []) else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"ap:{ch_id}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"filtered:{ch_id}")
    kb.adjust(1)
    return kb

def build_admin_gear_keyboard(ch_id: int, uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    channel = channel or {"gear": []}
    for code, name in GEAR_CODE_TO_NAME.items():
        mark = "✅" if name in channel.get("gear", []) else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"ag:{ch_id}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"filtered:{ch_id}")
    kb.adjust(1)
    return kb

def build_admin_rarity_keyboard(ch_id: int, uid: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    channel = channel or {"rarities": []}
    for code, name in RARITY_CODE_TO_NAME.items():
        mark = "✅" if name in channel.get("rarities", []) else "❌"
        kb.button(text=f"{mark} {name}", callback_data=f"ar:{ch_id}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"filtered:{ch_id}")
    kb.adjust(2)
    return kb

@dp.callback_query(lambda c: c.data and c.data.startswith("plants:"))
async def cb_admin_plants(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    kb = build_admin_plants_keyboard(ch_id, uid)
    try:
        await callback.message.answer("🌿 Выбери растения:", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("gear:"))
async def cb_admin_gear(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    kb = build_admin_gear_keyboard(ch_id, uid)
    try:
        await callback.message.answer("⚔️ Выбери предметы:", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("rarity:"))
async def cb_admin_rarity(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    kb = build_admin_rarity_keyboard(ch_id, uid)
    try:
        await callback.message.answer("🎖 Выбери редкости:", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

# admin toggle handlers (ap, ag, ar)
@dp.callback_query(lambda c: c.data and c.data.startswith("ap:"))
async def cb_admin_toggle_plant(callback: types.CallbackQuery):
    # ap:ch_id:pc
    try:
        _, ch_id_s, code = callback.data.split(":",2)
        ch_id = int(ch_id_s)
    except Exception:
        await callback.answer()
        return
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel is None:
        await callback.answer("Канал не найден.")
        return
    name = PLANT_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    channel.setdefault("plants", [])
    if name in channel["plants"]:
        channel["plants"].remove(name)
    else:
        channel["plants"].append(name)
    channel["mode"] = "custom"
    save_settings()
    kb = build_admin_plants_keyboard(ch_id, uid)
    try:
        await callback.message.edit_text("🌿 Выбери растения:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("ag:"))
async def cb_admin_toggle_gear(callback: types.CallbackQuery):
    try:
        _, ch_id_s, code = callback.data.split(":",2)
        ch_id = int(ch_id_s)
    except Exception:
        await callback.answer()
        return
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel is None:
        await callback.answer("Канал не найден.")
        return
    name = GEAR_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    channel.setdefault("gear", [])
    if name in channel["gear"]:
        channel["gear"].remove(name)
    else:
        channel["gear"].append(name)
    channel["mode"] = "custom"
    save_settings()
    kb = build_admin_gear_keyboard(ch_id, uid)
    try:
        await callback.message.edit_text("⚔️ Выбери предметы:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("ar:"))
async def cb_admin_toggle_rarity(callback: types.CallbackQuery):
    try:
        _, ch_id_s, code = callback.data.split(":",2)
        ch_id = int(ch_id_s)
    except Exception:
        await callback.answer()
        return
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel is None:
        await callback.answer("Канал не найден.")
        return
    name = RARITY_CODE_TO_NAME.get(code)
    if not name:
        await callback.answer()
        return
    channel.setdefault("rarities", [])
    if name in channel["rarities"]:
        channel["rarities"].remove(name)
    else:
        channel["rarities"].append(name)
    channel["mode"] = "custom"
    save_settings()
    kb = build_admin_rarity_keyboard(ch_id, uid)
    try:
        await callback.message.edit_text("🎖 Выбери редкости:", reply_markup=safe_markup(kb))
    except Exception:
        await callback.answer("Обновлено")
    await callback.answer("Обновлено")

@dp.callback_query(lambda c: c.data and c.data.startswith("autodelete:"))
async def cb_autodelete(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if channel is None:
        await callback.answer("Канал не найден.")
        return
    channel.setdefault("autodelete", True)
    channel.setdefault("autodelete_delay", 5)
    kb = InlineKeyboardBuilder()
    state = "Вкл" if channel["autodelete"] else "Выкл"
    kb.button(text=f"🔄 {state}", callback_data=f"toggle_autodelete:{ch_id}")
    kb.button(text="✍ Изменить время (мин)", callback_data=f"change_delay:{ch_id}")
    kb.button(text="⬅️ Назад", callback_data=f"config:{ch_id}")
    kb.adjust(1)
    try:
        await callback.message.answer(f"⏱ Автоудаление: {state}, время: {channel['autodelete_delay']} мин", reply_markup=safe_markup(kb))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("toggle_autodelete:"))
async def cb_toggle_autodelete(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if not channel:
        await callback.answer("Канал не найден.")
        return
    channel["autodelete"] = not channel.get("autodelete", True)
    save_settings()
    await cb_autodelete(callback)

@dp.callback_query(lambda c: c.data and c.data.startswith("change_delay:"))
async def cb_change_delay(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    pending_actions[callback.from_user.id] = f"delay:{ch_id}"
    try:
        await callback.message.answer("Введи время удаления в минутах (целое число), например: 5")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("testchannel:"))
async def cb_testchannel(callback: types.CallbackQuery):
    ch_id = int(callback.data.split(":",1)[1])
    uid = str(callback.from_user.id)
    channel = next((c for c in user_channels.get(uid,[]) if c["id"] == ch_id), None)
    if not channel:
        try:
            await callback.message.answer("Канал не найден.")
        except Exception:
            pass
        await callback.answer()
        return
    data = await get_stocks()
    if not data:
        await callback.message.answer("Ошибка API.")
        await callback.answer()
        return
    text = format_stocks(data, channel)
    if not text:
        await callback.message.answer("По текущим фильтрам нет позиций.")
        await callback.answer()
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="Перейти в бота", url=BOT_PROMO_LINK)
    try:
        await bot.send_message(channel["id"], text, parse_mode="HTML", reply_markup=safe_markup(kb))
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки в канал: {e}")
        await callback.answer()
        return
    await callback.message.answer(f"✅ Отправлено в {ch_id}")
    await callback.answer()

@dp.message(Command("addadmin"))
async def cmd_addadmin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /addadmin <id>")
        return
    try:
        new_admin = int(parts[1])
        if new_admin not in ADMINS:
            ADMINS.append(new_admin)
            save_admins()
            await message.answer(f"✅ {new_admin} добавлен в админы.")
        else:
            await message.answer("Уже админ.")
    except Exception:
        await message.answer("Неверный id.")

# auto posting loop
async def auto_post_stocks():
    last_data = None
    while True:
        loop_time = asyncio.get_event_loop().time()
        wait_time = UPDATE_INTERVAL_MINUTES * 60 - (loop_time % (UPDATE_INTERVAL_MINUTES * 60))
        if wait_time < 1:
            wait_time = UPDATE_INTERVAL_MINUTES * 60
        await asyncio.sleep(wait_time)
        new_data = await get_stocks()
        if new_data:
            last_data = new_data
        if not last_data:
            continue
        # post to configured channels
        for _, channels in list(user_channels.items()):
            for ch in channels:
                try:
                    ch.setdefault("plants", [])
                    ch.setdefault("gear", [])
                    ch.setdefault("rarities", [])
                    ch.setdefault("autodelete", True)
                    ch.setdefault("autodelete_delay", 5)
                    text = format_stocks(last_data, ch)
                    if not text:
                        continue
                    kb = InlineKeyboardBuilder()
                    kb.button(text="Перейти в бота", url=BOT_PROMO_LINK)
                    try:
                        await bot.send_message(ch["id"], text, parse_mode="HTML", reply_markup=safe_markup(kb))
                    except Exception as e:
                        print(f"auto_post error for {ch.get('id')}: {e}")
                except Exception as e:
                    print(f"auto_post channel loop error: {e}")
        # post to users
        for uid_str, usettings in list(user_settings.items()):
            try:
                if not usettings.get("receive", False):
                    continue
                ok, missing = await check_user_subs(int(uid_str))
                if not ok:
                    continue
                text = format_stocks(last_data, usettings)
                if not text:
                    continue
                msg = await bot.send_message(int(uid_str), text, parse_mode="HTML")
                if usettings.get("autodelete", True):
                    delay_minutes = usettings.get("autodelete_delay", 5)
                    asyncio.create_task(delete_later(msg.chat.id, msg.message_id, delay_minutes * 60))
            except Exception as e:
                print(f"error sending to user {uid_str}: {e}")

async def main():
    asyncio.create_task(auto_post_stocks())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
