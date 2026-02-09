from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters as tg_filters
)
import json, os

# ================= تنظیمات =================
# BOT_TOKEN و OWNER_USERNAME از متغیر محیطی می‌آیند
BOT_TOKEN = os.environ.get("BOT_TOKEN")            # مقدار از Environment Variable
OWNER_USERNAME = os.environ.get("OWNER_USERNAME")  # بدون @

# فایل‌های ذخیره‌سازی
ADMINS_FILE = "admins.json"
FILMS_FILE = "films.json"

# ================= ابزار فایل =================
def load(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(file, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default

def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

admins = load(ADMINS_FILE, {})
films = load(FILMS_FILE, {})

# ================= دسترسی‌ها =================
def is_owner(username):
    return username == OWNER_USERNAME or (
        username in admins and admins[username]["role"] == "owner"
    )

def is_admin(username):
    return username in admins and admins[username]["role"] == "admin"

def has_privilege(username):
    return is_owner(username) or is_admin(username)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    username = user.username

    if not username:
        await update.message.reply_text("❌ اکانت شما یوزرنیم ندارد")
        return

    if is_owner(username):
        keyboard = [
            [InlineKeyboardButton("🎬 ثبت فیلم", callback_data="add_film")],
            [InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data="admin_panel")],
            [InlineKeyboardButton("👑 مدیریت مالک‌ها", callback_data="owner_panel")]
        ]
        await update.message.reply_text(
            "👑 پنل مدیریت مالک",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if is_admin(username):
        keyboard = [
            [InlineKeyboardButton("🎬 ثبت فیلم", callback_data="add_film")]
        ]
        await update.message.reply_text(
            "🎬 پنل ادمین",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "❌ شما دسترسی ندارید\nبرای دریافت دسترسی با مالک ربات تماس بگیرید"
    )

# ================= ثبت فیلم =================
async def add_film(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["step"] = "names"
    await q.edit_message_text("🎬 نام فیلم را وارد کنید\n(چند نام با , جدا شود)")

async def film_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not has_privilege(username):
        return

    step = context.user_data.get("step")
    if not step:
        return

    if step == "names":
        context.user_data["names"] = [
            n.strip() for n in update.message.text.split(",") if n.strip()
        ]
        context.user_data["step"] = "link"
        await update.message.reply_text("🔗 لینک فیلم را ارسال کنید")
        return

    if step == "link":
        link = update.message.text.strip()
        for name in context.user_data["names"]:
            films[name] = link
        save(FILMS_FILE, films)
        context.user_data.clear()
        await update.message.reply_text("✅ فیلم با موفقیت ثبت شد")

# ================= جستجو =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not has_privilege(username):
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    if not context.args:
        return

    name = " ".join(context.args)
    if name in films:
        await update.message.reply_text(films[name])
    else:
        await update.message.reply_text("❌ چیزی پیدا نشد")

# ================= مدیریت ادمین =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    text = "👥 لیست ادمین‌ها:\n\n"
    found = False
    for u, d in admins.items():
        if d["role"] == "admin":
            text += f"• @{u}\n"
            found = True
    if not found:
        text += "— ادمینی وجود ندارد"

    keyboard = [
        [InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")],
        [InlineKeyboardButton("⬅ بازگشت", callback_data="back")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["add_admin"] = True
    await q.edit_message_text("🆔 یوزرنیم ادمین جدید را بدون @ ارسال کنید")

async def receive_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("add_admin"):
        return

    username = update.message.text.replace("@", "").strip()
    admins[username] = {"role": "admin"}
    save(ADMINS_FILE, admins)

    context.user_data.clear()
    await update.message.reply_text(f"✅ @{username} ادمین شد")

# ================= مدیریت مالک =================
async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    text = "👑 لیست مالک‌ها:\n\n"
    text += f"• @{OWNER_USERNAME} (مالک اصلی)\n"
    for u, d in admins.items():
        if d["role"] == "owner":
            text += f"• @{u}\n"

    keyboard = [
        [InlineKeyboardButton("➕ افزودن مالک", callback_data="add_owner")],
        [InlineKeyboardButton("❌ حذف مالک", callback_data="del_owner")],
        [InlineKeyboardButton("⬅ بازگشت", callback_data="back")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["add_owner"] = True
    await q.edit_message_text("🆔 یوزرنیم مالک جدید را بدون @ ارسال کنید")

async def del_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["del_owner"] = True
    await q.edit_message_text("🆔 یوزرنیم مالک برای حذف را بدون @ ارسال کنید")

async def receive_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace("@", "").strip()

    if context.user_data.get("add_owner"):
        admins[username] = {"role": "owner"}
        save(ADMINS_FILE, admins)
        await update.message.reply_text(f"✅ @{username} مالک شد")

    elif context.user_data.get("del_owner"):
        if username == OWNER_USERNAME:
            await update.message.reply_text("❌ مالک اصلی قابل حذف نیست")
        elif username in admins and admins[username]["role"] == "owner":
            del admins[username]
            save(ADMINS_FILE, admins)
            await update.message.reply_text(f"✅ @{username} حذف شد")
        else:
            await update.message.reply_text("❌ مالک یافت نشد")

    context.user_data.clear()

# ================= بازگشت =================
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await start(update, context)

# ================= اجرا =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

# هَندلرها
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("search", search))
app.add_handler(CallbackQueryHandler(add_film, pattern="add_film"))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
app.add_handler(CallbackQueryHandler(owner_panel, pattern="owner_panel"))
app.add_handler(CallbackQueryHandler(add_admin, pattern="add_admin"))
app.add_handler(CallbackQueryHandler(add_owner, pattern="add_owner"))
app.add_handler(CallbackQueryHandler(del_owner, pattern="del_owner"))
app.add_handler(CallbackQueryHandler(back, pattern="back"))

app.add_handler(MessageHandler(tg_filters.TEXT & tg_filters.ChatType.PRIVATE, film_steps))
app.add_handler(MessageHandler(tg_filters.TEXT & tg_filters.ChatType.PRIVATE, receive_admin))
app.add_handler(MessageHandler(tg_filters.TEXT & tg_filters.ChatType.PRIVATE, receive_owner))

print("Bot is running...")
app.run_polling()