# دالة طباعة chat_id لأي رسالة (مؤقتة)



import sys
import traceback
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()


# متغير لتتبع حالة انتظار وصف المشكلة لكل مستخدم
user_report_state = {}

# chat_id الخاص بالمجموعة التي ستستقبل البلاغات
REPORT_GROUP_CHAT_ID = -1003070936656

# طباعة أي استثناء يحدث في البرنامج
def excepthook(type, value, tb):
    traceback.print_exception(type, value, tb)
sys.excepthook = excepthook
print("Bot is starting...")

# اقرأ التوكن من متغير البيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# المسار الجذري للملفات (يمكن تعديله لاحقًا)
ROOT_DIR = os.path.join(os.path.dirname(__file__), "files")  # المسار المطلق لمجلد الملفات

def list_dir(abs_path):
    """إرجاع قائمة الملفات والمجلدات في المسار المطلق المحدد"""
    items = []
    for name in os.listdir(abs_path):
        full_path = os.path.join(abs_path, name)
        if os.path.isdir(full_path):
            items.append((name, 'folder'))
        else:
            items.append((name, 'file'))
    return items


# خريطة تربط كل معرف قصير بالمسار الفعلي
id_to_path = {}

def build_keyboard(abs_path):
    """بناء أزرار المجلدات والملفات باستخدام base64 في callback_data"""
    rel_path = os.path.relpath(abs_path, ROOT_DIR)
    items = list_dir(abs_path)
    # ترتيب المجلدات أولاً ثم الملفات، كل مجموعة مرتبة أبجديًا
    folders = sorted([item for item in items if item[1] == 'folder'], key=lambda x: x[0].lower())
    files = sorted([item for item in items if item[1] == 'file'], key=lambda x: x[0].lower())
    keyboard = []
    for name, kind in folders:
        item_rel_path = os.path.normpath(os.path.join(rel_path, name)) if rel_path != '.' else name
        item_id = str(uuid.uuid4())[:8]
        id_to_path[item_id] = item_rel_path
        keyboard.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"FOLDER|{item_id}")])
    for name, kind in files:
        item_rel_path = os.path.normpath(os.path.join(rel_path, name)) if rel_path != '.' else name
        item_id = str(uuid.uuid4())[:8]
        id_to_path[item_id] = item_rel_path
        keyboard.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"FILE|{item_id}")])
    if rel_path != '.':
        parent_rel = os.path.dirname(rel_path)
        parent_id = str(uuid.uuid4())[:8]
        id_to_path[parent_id] = parent_rel
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f"FOLDER|{parent_id}")])
    # زر التبليغ عن مشكلة في كل قائمة
    keyboard.append([InlineKeyboardButton("🚩 تبليغ عن مشكلة", callback_data="REPORT|0")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "اختر مجلد أو ملف:",
        reply_markup=build_keyboard(ROOT_DIR)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    kind, item_id = data.split("|", 1)
    if kind == "REPORT":
        user_id = query.from_user.id
        user_report_state[user_id] = True
        await query.message.reply_text("يرجى كتابة وصف المشكلة بالتفصيل، وسيتم إرسالها للمسؤول.")
        return
    rel_path = id_to_path.get(item_id, '')
    abs_path = os.path.join(ROOT_DIR, rel_path) if rel_path else ROOT_DIR
    if kind == "FOLDER":
        await query.edit_message_reply_markup(reply_markup=build_keyboard(abs_path))
    elif kind == "FILE":
        await query.message.reply_document(document=open(abs_path, "rb"))
        # بعد إرسال الملف، العودة لقائمة المجلد الفرعي (الأب) للمجلد العميق
        parent_abs = os.path.dirname(os.path.dirname(abs_path))
        await query.edit_message_reply_markup(reply_markup=build_keyboard(parent_abs))

# استقبال وصف المشكلة من المستخدم
async def handle_report_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_report_state.get(user_id):
        user = update.effective_user
        msg = f"🚩 بلاغ جديد من المستخدم: {user.full_name} (id: {user.id})\n" \
              f"username: @{user.username if user.username else '-'}\n" \
              f"النص: {update.message.text}"
        await context.bot.send_message(chat_id=REPORT_GROUP_CHAT_ID, text=msg)
        await update.message.reply_text("شكرًا لك، تم استلام بلاغك وسيتم مراجعته.")
        user_report_state[user_id] = False



if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_report_message))
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()
    app.add_handler(MessageHandler(filters.ALL, print_chat_id))

    app = ApplicationBuilder().token("8321747832:AAEv2ahKJu777s5wve9iHvSwIrix-QCpiy8").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()
