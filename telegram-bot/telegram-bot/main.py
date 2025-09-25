git push# دالة طباعة chat_id لأي رسالة (مؤقتة)



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

FILES_PER_PAGE = 5

# تعديل وظيفة build_keyboard لتقسيم الملفات إلى صفحات

def build_keyboard(abs_path, current_page=1):
    """بناء أزرار المجلدات والملفات باستخدام base64 في callback_data"""
    rel_path = os.path.relpath(abs_path, ROOT_DIR)
    items = list_dir(abs_path)
    # ترتيب المجلدات أولاً ثم الملفات، كل مجموعة مرتبة أبجديًا
    folders = sorted([item for item in items if item[1] == 'folder'], key=lambda x: x[0].lower())
    files = sorted([item for item in items if item[1] == 'file'], key=lambda x: x[0].lower())
    all_items = folders + files

    # تقسيم العناصر إلى صفحات
    total_pages = (len(all_items) + FILES_PER_PAGE - 1) // FILES_PER_PAGE
    start_index = (current_page - 1) * FILES_PER_PAGE
    end_index = start_index + FILES_PER_PAGE
    page_items = all_items[start_index:end_index]

    keyboard = []
    for name, kind in page_items:
        item_rel_path = os.path.normpath(os.path.join(rel_path, name)) if rel_path != '.' else name
        item_id = str(uuid.uuid4())[:8]
        id_to_path[item_id] = item_rel_path
        if kind == 'folder':
            keyboard.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"FOLDER|{item_id}|{current_page}")])
        else:
            keyboard.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"FILE|{item_id}|{current_page}")])

    # إضافة أزرار التنقل بين الصفحات
    navigation_buttons = []
    if current_page > 1:
        navigation_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"NAV|{current_page - 1}"))
    if current_page < total_pages:
        navigation_buttons.append(InlineKeyboardButton("➡️ التالي", callback_data=f"NAV|{current_page + 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)

    # زر التبليغ عن مشكلة في كل قائمة
    keyboard.append([InlineKeyboardButton("🚩 تبليغ عن مشكلة", callback_data="REPORT|0")])

    return InlineKeyboardMarkup(keyboard)

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



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "اختر مجلد أو ملف:",
        reply_markup=build_keyboard(ROOT_DIR)
    )

# تعديل وظيفة handle_button للتعامل مع التنقل بين الصفحات
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    kind, item_id, *page_info = data.split("|")
    current_page = int(page_info[0]) if page_info else 1

    if kind == "NAV":
        abs_path = ROOT_DIR
        await query.edit_message_reply_markup(reply_markup=build_keyboard(abs_path, current_page=int(item_id)))
        return

    if kind == "REPORT":
        user_id = query.from_user.id
        user_report_state[user_id] = True
        await query.message.reply_text("يرجى كتابة وصف المشكلة بالتفصيل، وسيتم إرسالها للمسؤول.")
        return

    rel_path = id_to_path.get(item_id, '')
    abs_path = os.path.join(ROOT_DIR, rel_path) if rel_path else ROOT_DIR
    if kind == "FOLDER":
        await query.edit_message_reply_markup(reply_markup=build_keyboard(abs_path, current_page))
    elif kind == "FILE":
        await query.message.reply_document(document=open(abs_path, "rb"))
        parent_abs = os.path.dirname(os.path.dirname(abs_path))
        await query.edit_message_reply_markup(reply_markup=build_keyboard(parent_abs, current_page))


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_report_message))
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()
