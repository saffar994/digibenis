import asyncio
import json
import os
import math
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from aiohttp_socks import ProxyConnector
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# —— Config ————————————————————————————————————————
BOT_TOKEN    = os.getenv("BOT_TOKEN", "6729658313:AAE_Lyl0dBhGU6mabVvRmEhBIvSqrQgGngE")
SUPER_ADMIN  = int(os.getenv("SUPER_ADMIN_ID", "564736869"))

BRANCHES_FILE = "branches.json"
SERVICES_FILE = "services.json"
ORDERS_FILE   = "orders.json"

# —— States ————————————————————————————————————————
class OrderState(StatesGroup):
    choosing_category  = State()
    choosing_service   = State()
    entering_details   = State()
    uploading_file     = State()
    sending_location   = State()

# —— Helpers ———————————————————————————————————————
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def nearest_branch(lat, lon):
    branches = load_json(BRANCHES_FILE)
    active = [b for b in branches if b.get("active", True)]
    if not active:
        return None
    return min(active, key=lambda b: haversine(lat, lon, b["lat"], b["lon"]))

def new_order_id():
    orders = load_json(ORDERS_FILE)
    return f"ORD{len(orders)+1:04d}"

# —— Bot & Dispatcher ——————————————————————————————
def create_bot():
    if PROXY_AVAILABLE:
        try:
            connector = ProxyConnector.from_url("socks5://127.0.0.1:9909")
            session = AiohttpSession(connector=connector)
            print("✅ پروکسی Geph فعال شد (پورت 9909)")
            return Bot(token=BOT_TOKEN, session=session)
        except Exception as e:
            print(f"⚠️ خطا در پروکسی: {e} — بدون پروکسی ادامه میدیم")
    return Bot(token=BOT_TOKEN)

bot = create_bot()
dp  = Dispatcher(storage=MemoryStorage())

# —— /start ————————————————————————————————————————
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 ثبت سفارش")],
            [KeyboardButton(text="📋 سفارش‌های من")],
            [KeyboardButton(text="🏪 شعبه‌ها"), KeyboardButton(text="📞 پشتیبانی")],
        ],
        resize_keyboard=True
    )
    await msg.answer(
        f"سلام {msg.from_user.first_name} عزیز! 👋\nبه دیجی‌بنیس خوش آمدید 🖨️",
        reply_markup=kb
    )

# —— ثبت سفارش ————————————————————————————————————
@dp.message(F.text == "🛒 ثبت سفارش")
async def start_order(msg: Message, state: FSMContext):
    services = load_json(SERVICES_FILE)
    categories = list(dict.fromkeys(s["category"] for s in services if s.get("active", True)))
    if not categories:
        await msg.answer("در حال حاضر سرویسی موجود نیست.")
        return
    buttons = [[InlineKeyboardButton(text=c, callback_data=f"cat:{c}")] for c in categories]
    await msg.answer("📂 دسته‌بندی مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(OrderState.choosing_category)

@dp.callback_query(F.data.startswith("cat:"), OrderState.choosing_category)
async def choose_category(cb: CallbackQuery, state: FSMContext):
    category = cb.data.split(":", 1)[1]
    await state.update_data(category=category)
    services = [s for s in load_json(SERVICES_FILE) if s["category"] == category and s.get("active", True)]
    buttons = [[InlineKeyboardButton(text=f"{s['name']} — {s['price']:,} ت", callback_data=f"svc:{s['id']}")] for s in services]
    await cb.message.edit_text("🔧 سرویس مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(OrderState.choosing_service)
    await cb.answer()

@dp.callback_query(F.data.startswith("svc:"), OrderState.choosing_service)
async def choose_service(cb: CallbackQuery, state: FSMContext):
    svc_id = cb.data.split(":", 1)[1]
    services = load_json(SERVICES_FILE)
    svc = next((s for s in services if s["id"] == svc_id), None)
    if not svc:
        await cb.answer("سرویس یافت نشد!")
        return
    await state.update_data(service_id=svc_id, service_name=svc["name"], price=svc["price"], needs_file=svc.get("needs_file", False))
    await cb.message.edit_text(f"✅ انتخاب شد: *{svc['name']}*\n\nتعداد و توضیحات را بنویسید:", parse_mode="Markdown")
    await state.set_state(OrderState.entering_details)
    await cb.answer()

@dp.message(OrderState.entering_details)
async def enter_details(msg: Message, state: FSMContext):
    await state.update_data(details=msg.text)
    data = await state.get_data()
    if data.get("needs_file"):
        await msg.answer("📎 لطفاً فایل خود را ارسال کنید:")
        await state.set_state(OrderState.uploading_file)
    else:
        await ask_location(msg, state)

@dp.message(OrderState.uploading_file)
async def upload_file(msg: Message, state: FSMContext):
    file_id = None
    if msg.document:
        file_id = msg.document.file_id
    elif msg.photo:
        file_id = msg.photo[-1].file_id
    if file_id:
        await state.update_data(file_id=file_id)
    await ask_location(msg, state)

async def ask_location(msg: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 ارسال موقعیت مکانی", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await msg.answer("📍 موقعیت مکانی خود را ارسال کنید تا نزدیک‌ترین شعبه پیدا شود:", reply_markup=kb)
    await state.set_state(OrderState.sending_location)

@dp.message(OrderState.sending_location, F.location)
async def receive_location(msg: Message, state: FSMContext):
    lat, lon = msg.location.latitude, msg.location.longitude
    branch = nearest_branch(lat, lon)
    if not branch:
        await msg.answer("متأسفانه شعبه فعالی یافت نشد.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    data = await state.get_data()
    order_id = new_order_id()
    order = {
        "id": order_id,
        "user_id": msg.from_user.id,
        "user_name": msg.from_user.full_name,
        "service_id": data.get("service_id"),
        "service_name": data.get("service_name"),
        "price": data.get("price"),
        "details": data.get("details"),
        "file_id": data.get("file_id"),
        "branch_id": branch["id"],
        "branch_name": branch["name"],
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    orders = load_json(ORDERS_FILE)
    orders.append(order)
    save_json(ORDERS_FILE, orders)

    await msg.answer(
        f"✅ سفارش *{order_id}* ثبت شد!\n\n"
        f"🏪 شعبه: {branch['name']}\n"
        f"🔧 سرویس: {data.get('service_name')}\n"
        f"💰 قیمت: {data.get('price'):,} تومان\n\n"
        f"به زودی با شما تماس گرفته می‌شود.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    # اطلاع به ادمین شعبه
    admin_id = branch.get("admin_id")
    if admin_id:
        text = f"🔔 سفارش جدید: *{order_id}*\n👤 {msg.from_user.full_name}\n🔧 {data.get('service_name')}\n📝 {data.get('details')}"
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
            if data.get("file_id"):
                await bot.send_document(admin_id, data["file_id"])
        except Exception:
            pass

    await state.clear()

# —— سفارش‌های من ——————————————————————————————————
@dp.message(F.text == "📋 سفارش‌های من")
async def my_orders(msg: Message):
    orders = [o for o in load_json(ORDERS_FILE) if o["user_id"] == msg.from_user.id]
    if not orders:
        await msg.answer("سفارشی ندارید.")
        return
    status_map = {"pending": "⏳ در انتظار", "processing": "🔄 در حال انجام", "ready": "✅ آماده", "rejected": "❌ رد شده"}
    text = "📋 *سفارش‌های اخیر شما:*\n\n"
    for o in orders[-5:]:
        text += f"• {o['id']} — {o['service_name']}\n  🏪 {o['branch_name']}\n  {status_map.get(o['status'], o['status'])}\n\n"
    await msg.answer(text, parse_mode="Markdown")

# —— شعبه‌ها ———————————————————————————————————————
@dp.message(F.text == "🏪 شعبه‌ها")
async def show_branches(msg: Message):
    branches = [b for b in load_json(BRANCHES_FILE) if b.get("active", True)]
    if not branches:
        await msg.answer("شعبه فعالی یافت نشد.")
        return
    text = "*🏪 شعبه‌های Digibenis:*\n\n"
    for b in branches:
        text += f"• *{b['name']}*\n  📍 {b['address']}\n  📞 {b.get('phone', 'ندارد')}\n\n"
    await msg.answer(text, parse_mode="Markdown")

# —— پشتیبانی ——————————————————————————————————————
@dp.message(F.text == "📞 پشتیبانی")
async def support(msg: Message):
    await msg.answer(
        "*📞 پشتیبانی Digibenis*\n\nلطفاً سؤال خود را مطرح کنید.\nکارشناسان ما در اسرع وقت پاسخگو خواهند بود.",
        parse_mode="Markdown"
    )

# —— آمار ادمین ————————————————————————————————————
@dp.message(Command("stats"))
async def admin_stats(msg: Message):
    if msg.from_user.id != SUPER_ADMIN:
        return
    orders = load_json(ORDERS_FILE)
    total   = len(orders)
    pending = sum(1 for o in orders if o["status"] == "pending")
    ready   = sum(1 for o in orders if o["status"] == "ready")
    await msg.answer(
        f"📊 *آمار سفارشات:*\n\nکل: {total}\nدر انتظار: {pending}\nآماده: {ready}",
        parse_mode="Markdown"
    )

# —— main ——————————————————————————————————————————
async def main():
    print("🚀 Digibenis bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
