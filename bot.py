import asyncio
import json
import os
import math
from datetime import datetime
from aiogram import Bot, Dispatcher, F
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

# ─── Config ───────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUPER_ADMIN = int(os.getenv("SUPER_ADMIN_ID", "000000000"))

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ─── States ───────────────────────────────────────────────
class OrderState(StatesGroup):
    choosing_category = State()
    choosing_service  = State()
    entering_details  = State()
    uploading_file    = State()
    sending_location  = State()
    confirming_order  = State()
    waiting_receipt   = State()

# ─── Data helpers ─────────────────────────────────────────
BRANCHES_FILE  = "branches.json"
SERVICES_FILE  = "services.json"
ORDERS_FILE    = "orders.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def next_order_id():
    orders = load_json(ORDERS_FILE)
    return f"DGB-{len(orders)+1:04d}"

# ─── Distance calculation (Haversine) ─────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_nearest_branch(user_lat, user_lon):
    branches = load_json(BRANCHES_FILE)
    active = [b for b in branches if b.get("active", True)]
    if not active:
        return None, None
    distances = [
        (b, haversine(user_lat, user_lon, b["lat"], b["lon"]))
        for b in active
    ]
    distances.sort(key=lambda x: x[1])
    return distances[0]  # (branch, km)

# ─── Keyboards ────────────────────────────────────────────
def main_menu_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 ثبت سفارش جدید")],
        [KeyboardButton(text="📦 سفارش‌های من"), KeyboardButton(text="🏪 شعبه‌ها")],
        [KeyboardButton(text="📞 پشتیبانی")],
    ], resize_keyboard=True)

def location_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 ارسال موقعیت من", request_location=True)],
        [KeyboardButton(text="🔙 بازگشت")],
    ], resize_keyboard=True)

def categories_kb():
    services = load_json(SERVICES_FILE)
    cats = list({s["category"] for s in services})
    buttons = [[InlineKeyboardButton(text=c, callback_data=f"cat_{c}")] for c in cats]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def services_kb(category):
    services = load_json(SERVICES_FILE)
    filtered = [s for s in services if s["category"] == category and s.get("active", True)]
    buttons = [
        [InlineKeyboardButton(
            text=f"{s['name']} — {s['price']:,} تومان",
            callback_data=f"svc_{s['id']}"
        )]
        for s in filtered
    ]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید سفارش",   callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ انصراف",         callback_data="cancel_order")],
    ])

def skip_file_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ بدون فایل ادامه بده", callback_data="skip_file")],
        [InlineKeyboardButton(text="❌ انصراف",              callback_data="cancel_order")],
    ])

def payment_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 پرداخت کردم، رسید می‌فرستم", callback_data=f"pay_{order_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_order")],
    ])

def admin_order_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید و آماده‌سازی", callback_data=f"adm_approve_{order_id}")],
        [InlineKeyboardButton(text="🔔 آماده تحویل",        callback_data=f"adm_ready_{order_id}")],
        [InlineKeyboardButton(text="❌ رد سفارش",            callback_data=f"adm_reject_{order_id}")],
    ])

# ─── /start ───────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        f"سلام {msg.from_user.first_name} 👋\n\n"
        "به *Digibenis* خوش آمدید!\n"
        "خدمات کپی، پرینت، چاپ، لوازم‌التحریر،\n"
        "لوازم کامپیوتر و موبایل — از نزدیک‌ترین شعبه 📍",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

# ─── New Order Flow ────────────────────────────────────────
@dp.message(F.text == "📋 ثبت سفارش جدید")
async def new_order(msg: Message, state: FSMContext):
    await state.set_state(OrderState.choosing_category)
    await msg.answer(
        "🗂 *دسته‌بندی خدمات:*\nچه نوع خدماتی نیاز دارید؟",
        parse_mode="Markdown",
        reply_markup=categories_kb()
    )

@dp.callback_query(F.data.startswith("cat_"), OrderState.choosing_category)
async def choose_category(cb: CallbackQuery, state: FSMContext):
    category = cb.data.split("cat_", 1)[1]
    await state.update_data(category=category)
    await state.set_state(OrderState.choosing_service)
    await cb.message.edit_text(
        f"📂 *{category}*\nیک سرویس انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=services_kb(category)
    )
    await cb.answer()

@dp.callback_query(F.data == "back_to_cats")
async def back_to_cats(cb: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.choosing_category)
    await cb.message.edit_text(
        "🗂 *دسته‌بندی خدمات:*",
        parse_mode="Markdown",
        reply_markup=categories_kb()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("svc_"), OrderState.choosing_service)
async def choose_service(cb: CallbackQuery, state: FSMContext):
    svc_id = cb.data.split("svc_", 1)[1]
    services = load_json(SERVICES_FILE)
    service = next((s for s in services if s["id"] == svc_id), None)
    if not service:
        await cb.answer("سرویس پیدا نشد!", show_alert=True)
        return

    await state.update_data(service_id=svc_id, service_name=service["name"],
                            service_price=service["price"], needs_file=service.get("needs_file", False))
    await state.set_state(OrderState.entering_details)
    await cb.message.edit_text(
        f"📝 *{service['name']}*\n\n"
        f"{service.get('description', '')}\n\n"
        "لطفاً *توضیحات سفارش* خود را بنویسید:\n"
        f"_(تعداد، رنگ، سایز، نوع کاغذ و ...)_",
        parse_mode="Markdown"
    )
    await cb.answer()

@dp.message(OrderState.entering_details)
async def get_details(msg: Message, state: FSMContext):
    await state.update_data(details=msg.text)
    data = await state.get_data()

    if data.get("needs_file"):
        await state.set_state(OrderState.uploading_file)
        await msg.answer(
            "📎 *فایل مورد نظر را ارسال کنید*\n_(عکس، PDF، Word ...)_\n\n"
            "اگر فایلی ندارید روی «بدون فایل» بزنید:",
            parse_mode="Markdown",
            reply_markup=skip_file_kb()
        )
    else:
        await state.set_state(OrderState.sending_location)
        await msg.answer(
            "📍 *موقعیت مکانی خود را ارسال کنید*\n"
            "تا نزدیک‌ترین شعبه پیدا شود:",
            parse_mode="Markdown",
            reply_markup=location_kb()
        )

@dp.message(OrderState.uploading_file, F.document | F.photo)
async def receive_file(msg: Message, state: FSMContext):
    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name
    else:
        file_id = msg.photo[-1].file_id
        file_name = "image.jpg"

    await state.update_data(file_id=file_id, file_name=file_name)
    await state.set_state(OrderState.sending_location)
    await msg.answer(
        "✅ فایل دریافت شد!\n\n"
        "📍 حالا *موقعیت مکانی* خود را ارسال کنید:",
        parse_mode="Markdown",
        reply_markup=location_kb()
    )

@dp.callback_query(F.data == "skip_file", OrderState.uploading_file)
async def skip_file(cb: CallbackQuery, state: FSMContext):
    await state.update_data(file_id=None, file_name=None)
    await state.set_state(OrderState.sending_location)
    await cb.message.answer(
        "📍 *موقعیت مکانی* خود را ارسال کنید\n"
        "تا نزدیک‌ترین شعبه پیدا شود:",
        parse_mode="Markdown",
        reply_markup=location_kb()
    )
    await cb.answer()

@dp.message(OrderState.sending_location, F.location)
async def receive_location(msg: Message, state: FSMContext):
    lat = msg.location.latitude
    lon = msg.location.longitude

    branch, distance = find_nearest_branch(lat, lon)
    if not branch:
        await msg.answer("❌ متأسفانه شعبه فعالی یافت نشد. با پشتیبانی تماس بگیرید.")
        return

    await state.update_data(
        user_lat=lat, user_lon=lon,
        branch_id=branch["id"],
        branch_name=branch["name"],
        branch_address=branch["address"],
        branch_admin=branch["admin_id"],
        distance=round(distance, 2)
    )

    data = await state.get_data()
    await state.set_state(OrderState.confirming_order)

    text = (
        f"📋 *خلاصه سفارش شما:*\n\n"
        f"🔧 سرویس: *{data['service_name']}*\n"
        f"📝 توضیحات: {data['details']}\n"
        f"📎 فایل: {'✅ دارد' if data.get('file_id') else '❌ ندارد'}\n\n"
        f"🏪 نزدیک‌ترین شعبه:\n"
        f"   *{branch['name']}*\n"
        f"   📍 {branch['address']}\n"
        f"   📏 فاصله: {distance:.1f} کیلومتر\n"
        f"   📞 {branch.get('phone', '—')}\n\n"
        f"💰 هزینه تخمینی: *{data['service_price']:,} تومان*\n\n"
        "آیا تأیید می‌کنید؟"
    )
    await msg.answer(text, parse_mode="Markdown",
                     reply_markup=confirm_kb())

@dp.message(OrderState.sending_location)
async def location_not_sent(msg: Message):
    await msg.answer("⚠️ لطفاً دکمه «📍 ارسال موقعیت من» را بزنید.")

# ─── Confirm order ─────────────────────────────────────────
@dp.callback_query(F.data == "confirm_order", OrderState.confirming_order)
async def confirm_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    order_id = next_order_id()
    order = {
        "id": order_id,
        "user_id": cb.from_user.id,
        "username": cb.from_user.username or "",
        "full_name": cb.from_user.full_name,
        "service_id": data["service_id"],
        "service_name": data["service_name"],
        "service_price": data["service_price"],
        "details": data["details"],
        "file_id": data.get("file_id"),
        "file_name": data.get("file_name"),
        "branch_id": data["branch_id"],
        "branch_name": data["branch_name"],
        "branch_address": data["branch_address"],
        "branch_admin": data["branch_admin"],
        "distance_km": data["distance"],
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }

    orders = load_json(ORDERS_FILE)
    orders.append(order)
    save_json(ORDERS_FILE, orders)

    # پیام به کاربر
    await cb.message.answer(
        f"✅ *سفارش ثبت شد!*\n\n"
        f"🔖 کد پیگیری: `{order_id}`\n"
        f"🏪 شعبه: {data['branch_name']}\n"
        f"📍 {data['branch_address']}\n\n"
        f"💰 مبلغ: *{data['service_price']:,} تومان*\n\n"
        "پس از آماده شدن سفارش اطلاع می‌دهیم. 🔔",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

    # پیام به ادمین شعبه
    admin_text = (
        f"🔔 *سفارش جدید — {order_id}*\n\n"
        f"👤 مشتری: {order['full_name']} (@{order['username']})\n"
        f"🔧 سرویس: {order['service_name']}\n"
        f"📝 توضیحات: {order['details']}\n"
        f"📎 فایل: {'✅' if order['file_id'] else '❌'}\n"
        f"💰 مبلغ: {order['service_price']:,} تومان\n"
        f"📏 فاصله مشتری: {order['distance_km']} km"
    )

    # اگر فایل دارد
    if order.get("file_id"):
        try:
            await bot.send_document(
                chat_id=data["branch_admin"],
                document=order["file_id"],
                caption=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_order_kb(order_id)
            )
        except Exception:
            await bot.send_message(
                chat_id=data["branch_admin"],
                text=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_order_kb(order_id)
            )
    else:
        await bot.send_message(
            chat_id=data["branch_admin"],
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=admin_order_kb(order_id)
        )

    # اطلاع به سوپر ادمین
    if SUPER_ADMIN:
        await bot.send_message(
            chat_id=SUPER_ADMIN,
            text=f"📊 سفارش جدید: `{order_id}` → شعبه: {data['branch_name']}",
            parse_mode="Markdown"
        )

    await cb.answer()

# ─── Cancel ───────────────────────────────────────────────
@dp.callback_query(F.data == "cancel_order")
async def cancel_order(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("❌ سفارش لغو شد.", reply_markup=main_menu_kb())
    await cb.answer()

@dp.message(F.text == "🔙 بازگشت")
async def go_back(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("به منوی اصلی بازگشتید.", reply_markup=main_menu_kb())

# ─── Admin callbacks ───────────────────────────────────────
async def is_branch_admin(user_id: int) -> bool:
    branches = load_json(BRANCHES_FILE)
    return any(b["admin_id"] == user_id for b in branches) or user_id == SUPER_ADMIN

@dp.callback_query(F.data.startswith("adm_approve_"))
async def admin_approve(cb: CallbackQuery):
    if not await is_branch_admin(cb.from_user.id):
        await cb.answer("دسترسی ندارید!", show_alert=True)
        return

    order_id = cb.data.split("adm_approve_")[1]
    orders = load_json(ORDERS_FILE)
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        await cb.answer("سفارش پیدا نشد!", show_alert=True)
        return

    order["status"] = "processing"
    save_json(ORDERS_FILE, orders)

    await bot.send_message(
        chat_id=order["user_id"],
        text=f"🔄 *سفارش شما در حال پردازش است!*\n\n"
             f"🔖 کد: `{order_id}`\n"
             f"🏪 شعبه: {order['branch_name']}\n\n"
             "به زودی آماده تحویل خواهد شد. ⏳",
        parse_mode="Markdown"
    )

    new_text = (cb.message.text or cb.message.caption or "") + "\n\n🔄 *در حال پردازش*"
    try:
        await cb.message.edit_text(new_text, parse_mode="Markdown",
                                   reply_markup=admin_order_kb(order_id))
    except Exception:
        await cb.message.edit_caption(new_text, parse_mode="Markdown",
                                      reply_markup=admin_order_kb(order_id))
    await cb.answer("سفارش تأیید شد ✅")

@dp.callback_query(F.data.startswith("adm_ready_"))
async def admin_ready(cb: CallbackQuery):
    if not await is_branch_admin(cb.from_user.id):
        await cb.answer("دسترسی ندارید!", show_alert=True)
        return

    order_id = cb.data.split("adm_ready_")[1]
    orders = load_json(ORDERS_FILE)
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        await cb.answer("سفارش پیدا نشد!", show_alert=True)
        return

    order["status"] = "ready"
    save_json(ORDERS_FILE, orders)

    await bot.send_message(
        chat_id=order["user_id"],
        text=f"✅ *سفارش شما آماده تحویل است!*\n\n"
             f"🔖 کد: `{order_id}`\n"
             f"🏪 شعبه: *{order['branch_name']}*\n"
             f"📍 {order['branch_address']}\n\n"
             "لطفاً جهت دریافت به شعبه مراجعه کنید. 🎉",
        parse_mode="Markdown"
    )
    await cb.answer("مشتری مطلع شد 🔔")

@dp.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject(cb: CallbackQuery):
    if not await is_branch_admin(cb.from_user.id):
        await cb.answer("دسترسی ندارید!", show_alert=True)
        return

    order_id = cb.data.split("adm_reject_")[1]
    orders = load_json(ORDERS_FILE)
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        await cb.answer("سفارش پیدا نشد!", show_alert=True)
        return

    order["status"] = "rejected"
    save_json(ORDERS_FILE, orders)

    await bot.send_message(
        chat_id=order["user_id"],
        text=f"❌ *سفارش شما رد شد.*\n\n"
             f"🔖 کد: `{order_id}`\n\n"
             "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
        parse_mode="Markdown"
    )
    await cb.answer("سفارش رد شد ❌")

# ─── My orders ─────────────────────────────────────────────
@dp.message(F.text == "📦 سفارش‌های من")
async def my_orders(msg: Message):
    orders = load_json(ORDERS_FILE)
    user_orders = [o for o in orders if o["user_id"] == msg.from_user.id]

    if not user_orders:
        await msg.answer("هنوز سفارشی ثبت نکرده‌اید.")
        return

    status_map = {
        "pending":    "⏳ در انتظار",
        "processing": "🔄 در حال پردازش",
        "ready":      "✅ آماده تحویل",
        "rejected":   "❌ رد شده"
    }

    text = "📦 *سفارش‌های اخیر شما:*\n\n"
    for o in user_orders[-5:]:
        text += (
            f"🔖 `{o['id']}` — {o['service_name']}\n"
            f"   🏪 {o['branch_name']}\n"
            f"   {status_map.get(o['status'], o['status'])}\n\n"
        )
    await msg.answer(text, parse_mode="Markdown")

# ─── Branches list ─────────────────────────────────────────
@dp.message(F.text == "🏪 شعبه‌ها")
async def show_branches(msg: Message):
    branches = load_json(BRANCHES_FILE)
    active = [b for b in branches if b.get("active", True)]

    if not active:
        await msg.answer("شعبه‌ای ثبت نشده است.")
        return

    text = "🏪 *شعبه‌های Digibenis:*\n\n"
    for b in active:
        text += (
            f"📍 *{b['name']}*\n"
            f"   {b['address']}\n"
            f"   📞 {b.get('phone', '—')}\n"
            f"   ⏰ {b.get('hours', '—')}\n\n"
        )
    await msg.answer(text, parse_mode="Markdown")

# ─── Support ──────────────────────────────────────────────
@dp.message(F.text == "📞 پشتیبانی")
async def support(msg: Message):
    await msg.answer(
        "📞 *پشتیبانی Digibenis*\n\n"
        "• تلگرام: @digibenis_support\n"
        "• ساعات پاسخگویی: ۸ تا ۲۲",
        parse_mode="Markdown"
    )

# ─── Super admin: stats ────────────────────────────────────
@dp.message(Command("stats"))
async def admin_stats(msg: Message):
    if msg.from_user.id != SUPER_ADMIN:
        return
    orders = load_json(ORDERS_FILE)
    total    = len(orders)
    pending  = sum(1 for o in orders if o["status"] == "pending")
    processing = sum(1 for o in orders if o["status"] == "processing")
    ready    = sum(1 for o in orders if o["status"] == "ready")
    rejected = sum(1 for o in orders if o["status"] == "rejected")

    await msg.answer(
        f"📊 *آمار کلی Digibenis:*\n\n"
        f"کل: {total}\n"
        f"⏳ در انتظار: {pending}\n"
        f"🔄 در پردازش: {processing}\n"
        f"✅ آماده: {ready}\n"
        f"❌ رد شده: {rejected}",
        parse_mode="Markdown"
    )

# ─── Run ──────────────────────────────────────────────────
async def main():
    print("🤖 Digibenis multi-branch bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
