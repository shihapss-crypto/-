import json
import os
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
DATA_FILE = "academy.json"
ADMIN_ID = 123456789  # ضع ID بتاعك هنا

students = [
    "Rasha Muneer","آلاء وليد","أحلام محمد","بتول إبراهيم",
    "تيسير حمود","حنين عبد الرحمن","رانيا حسن","سناء حسن",
    "عائدة عثمان","فائدة شيب","نبيلة محمد","ندى شريان",
    "ندي محمود","هديل فارس"
]

# ======================== STATE MACHINE ========================
SURAH_INPUT, FROM_INPUT, TO_INPUT = range(3)

# ======================== DATA MANAGEMENT ========================
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load()
today = str(date.today())

# تهيئة بيانات اليوم
if today not in data:
    data[today] = {
        s: {
            "status": "⬜",      # ⬜ حضور، ❌ غياب
            "surah": "البقرة",
            "from": "1",
            "to": "10"
        }
        for s in students
    }
    save(data)

# ======================== UI KEYBOARDS ========================
def main_menu():
    """القائمة الرئيسية"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 الحضور", callback_data="show")],
        [InlineKeyboardButton("📊 تقرير", callback_data="report")],
        [InlineKeyboardButton("🏆 ترتيب", callback_data="rank")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
    ])

def attendance_board():
    """لوحة الحضور التفاعلية"""
    keys = []
    for s in students:
        st = data[today][s]["status"]
        keys.append([InlineKeyboardButton(
            f"{s} {st}", 
            callback_data=f"toggle|{s}"
        )])
    keys.append([InlineKeyboardButton("🔙 عودة", callback_data="back")])
    return InlineKeyboardMarkup(keys)

def settings_menu():
    """قائمة الإعدادات"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تغيير السورة", callback_data="change_surah")],
        [InlineKeyboardButton("📝 تغيير الآيات", callback_data="change_verses")],
        [InlineKeyboardButton("🔙 عودة", callback_data="back")]
    ])

# ======================== COMMANDS ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    user_id = update.effective_user.id
    
    welcome_text = f"""👩‍🏫 **منصة أكاديمية الشهاب**

مرحباً بك يا {update.effective_user.first_name}! 👋
اختر من القائمة أدناه لإدارة الحضور والتقارير.

📅 التاريخ: {today}"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = """🆘 **قائمة المساعدة**

📖 **الحضور**: عرض قائمة الطالبات وتحديث الحضور
📊 **التقرير**: إحصائيات يومية
🏆 **الترتيب**: ترتيب الطالبات حسب أيام الحضور
⚙️ **الإعدادات**: تغيير السورة والآيات

الحالات:
• ⬜ = حضور
• ❌ = غياب"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ======================== CALLBACKS ========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار الرئيسي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # ============= ATTENDANCE =============
    if query.data == "show":
        current_surah = data[today].get(list(students)[0], {}).get("surah", "البقرة")
        current_from = data[today].get(list(students)[0], {}).get("from", "1")
        current_to = data[today].get(list(students)[0], {}).get("to", "10")
        
        text = f"""📖 **الحضور اليوم**

السورة: {current_surah}
من آية: {current_from} إلى {current_to}

اختر الطالبة لتبديل الحالة:"""
        
        await query.edit_message_text(text, reply_markup=attendance_board(), parse_mode="Markdown")
    
    # ============= TOGGLE ATTENDANCE =============
    elif query.data.startswith("toggle|"):
        name = query.data.split("|")[1]
        
        if data[today][name]["status"] == "⬜":
            data[today][name]["status"] = "❌"
        else:
            data[today][name]["status"] = "⬜"
        
        save(data)
        
        text = f"✅ تم تحديث حالة: {name}"
        await query.answer(text, show_alert=False)
        
        current_surah = data[today][list(students)[0]].get("surah", "البقرة")
        current_from = data[today][list(students)[0]].get("from", "1")
        current_to = data[today][list(students)[0]].get("to", "10")
        
        msg_text = f"""📖 **الحضور اليوم**

السورة: {current_surah}
من آية: {current_from} إلى {current_to}

اختر الطالبة لتبديل الحالة:"""
        
        await query.edit_message_reply_markup(reply_markup=attendance_board())
    
    # ============= REPORT =============
    elif query.data == "report":
        present = sum(1 for s in students if data[today][s]["status"] == "⬜")
        absent = len(students) - present
        percent = (present / len(students)) * 100
        
        current_surah = data[today][list(students)[0]].get("surah", "البقرة")
        
        text = f"""📊 **تقرير اليوم**

📅 التاريخ: {today}
📖 السورة: {current_surah}
✅ الحاضرات: {present}
❌ الغائبات: {absent}
📊 النسبة: {percent:.1f}%"""
        
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    # ============= RANKING =============
    elif query.data == "rank":
        scores = []
        for s in students:
            count = sum(1 for d in data if d <= today and s in data[d] and data[d][s]["status"] == "⬜")
            scores.append((s, count))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        text = "🏆 **ترتيب الطالبات**\n\n"
        for i, (name, count) in enumerate(scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "⭐"
            text += f"{medal} {i}. {name} — {count} أيام\n"
        
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    # ============= SETTINGS =============
    elif query.data == "settings":
        text = "⚙️ **الإعدادات**\n\nاختر ما تريد تغييره:"
        await query.edit_message_text(text, reply_markup=settings_menu(), parse_mode="Markdown")
    
    elif query.data == "change_surah":
        await query.edit_message_text(
            "📖 أدخل اسم السورة:\n(مثال: البقرة، آل عمران، النساء)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="back")]])
        )
        context.user_data['changing'] = 'surah'
        return SURAH_INPUT
    
    elif query.data == "change_verses":
        text = "📝 أدخل نطاق الآيات:\n(مثال: 1-10 أو 15-20)"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="back")]])
        )
        context.user_data['changing'] = 'verses'
        return FROM_INPUT
    
    # ============= BACK =============
    elif query.data == "back":
        await query.edit_message_text(
            "👩‍🏫 منصة أكاديمية الشهاب\n\nاختر من القائمة:",
            reply_markup=main_menu()
        )

# ======================== TEXT INPUT ========================
async def surah_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال اسم السورة"""
    surah_name = update.message.text.strip()
    
    # تحديث السورة لجميع الطالبات
    for student in students:
        data[today][student]["surah"] = surah_name
    
    save(data)
    
    text = f"✅ تم تحديث السورة إلى: **{surah_name}**"
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    return ConversationHandler.END

async def verses_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال نطاق الآيات"""
    verses_text = update.message.text.strip()
    
    try:
        from_v, to_v = verses_text.split("-")
        from_v = from_v.strip()
        to_v = to_v.strip()
        
        # تحديث الآيات لجميع الطالبات
        for student in students:
            data[today][student]["from"] = from_v
            data[today][student]["to"] = to_v
        
        save(data)
        
        text = f"✅ تم تحديث الآيات من **{from_v}** إلى **{to_v}**"
        await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    except ValueError:
        text = "❌ صيغة خاطئة! استخدم: 1-10"
        await update.message.reply_text(text)
        return FROM_INPUT
    
    return ConversationHandler.END

# ======================== SCHEDULED TASKS ========================
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """إرسال التقرير اليومي"""
    present = sum(1 for s in students if data[today][s]["status"] == "⬜")
    absent = len(students) - present
    percent = (present / len(students)) * 100
    
    text = f"""📤 **التقرير اليومي**

📅 التاريخ: {today}
✅ حضور: {present}
❌ غياب: {absent}
📊 نسبة: {percent:.1f}%"""
    
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="Markdown")
        print(f"✅ تم إرسال التقرير في {datetime.now()}")
    except Exception as e:
        print(f"❌ خطأ في إرسال التقرير: {e}")

# ======================== MAIN ========================
def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # معالج المحادثة للإعدادات
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^change_surah$")],
        states={
            SURAH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, surah_input)]
        },
        fallbacks=[CallbackQueryHandler(button_handler, pattern="^back$")]
    )
    
    conv_handler_verses = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^change_verses$")],
        states={
            FROM_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, verses_input)]
        },
        fallbacks=[CallbackQueryHandler(button_handler, pattern="^back$")]
    )
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(conv_handler_verses)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # إعداد الجدولة
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Africa/Cairo"))
    
    # إرسال التقرير في الساعة 3 مساءً يومياً
    scheduler.add_job(
        lambda: app.create_task(send_daily_report(app.context_types.DEFAULT_TYPE())),
        trigger="cron",
        hour=15,
        minute=0
    )
    
    scheduler.start()
    
    print("🚀 منصة أكاديمية الشهاب قيد التشغيل...")
    print(f"📅 التاريخ: {today}")
    print(f"👥 عدد الطالبات: {len(students)}")
    print("⏰ التقرير اليومي سيُرسل في الساعة 3 مساءً")
    
    # تشغيل البوت
    app.run_polling()

if __name__ == "__main__":
    main()
