##MESSAGE HANDLERS 
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
 
from core.services import *
from config import SYSTEM_PROMPT, CONTEXT, runtime
from models import ai_reply
from core.utils import * 
from core.storage import * 

logger = logging.getLogger("mediassistant")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    if not should_reply(update) or not can_send() or not check_message(update):
        return
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    lang = detect_language(text)
    
    # Fast path: greetings
    low = text.lower()
    greetings_en = ['hi', 'hello', 'hey', 'yo', 'hey there', 'clinic', 'assistant', 'doctor']
    greetings_am = ['ሰላም', 'እንደምን ነህ', 'እንደምን ናችሁ', 'ሰላም ነው']
    
    if low in greetings_en or any(g in text for g in greetings_am):
        await asyncio.sleep(0.5)
        if lang == "am":
            await update.message.reply_text("ሰላም! እንዴት ልረዳዎት እችላለሁ? 😊")
        else:
            await update.message.reply_text("Hey! How can I help you today? 😊")
        record_message()
        return
    
    # Fast path: thanks
    thanks_en = ['thanks', 'thank you', 'thx', 'great', 'good', 'thank u']
    thanks_am = ['አመሰግናለሁ', 'አመሰግናለው', 'እናመሰግናለን']
    
    if low in thanks_en or any(t in text for t in thanks_am):
        await asyncio.sleep(0.5)
        if lang == "am":
            await update.message.reply_text("ሌሎች አስፈላጊ ነገሮችን ልረዳዋት ዝግጁ ነኝ!")
        else:
            await update.message.reply_text("You're welcome! Always happy to help. 🙌")
        record_message()
        return
    
    # Check for appointment keywords
    appt_keywords_en = ['appointment', 'book', 'schedule', 'reserve', 'meet', 'visit']
    appt_keywords_am = ['ቀጠሮ']
    
    if any(k in text.lower() for k in appt_keywords_en) or any(k in text for k in appt_keywords_am):
        await handle_appointment_booking(update, context, lang)
        return
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Build messages with context
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    conv = await get_conversation(user_id)
    if conv:
        msgs.extend(list(conv)[-CONTEXT:])
    
    msgs.append({"role": "user", "content": text})
    
    # Get AI response
    response = await ai_reply(msgs, lang)
    
    if response:
        # Store conversation
        await add_to_conversation(user_id, "user", text)
        await add_to_conversation(user_id, "assistant", response)
        
        await asyncio.sleep(runtime.delay)
        await update.message.reply_text(response)
        record_message()
        logger.info("%s: %s... -> Replied (%s)", username, text[:50], lang)
    else:
        await asyncio.sleep(1)
        if lang == "am":
            await update.message.reply_text(
                "⚠️ እባክዎን ከታች ያለውን ሜኑ /menu ይጠቀው, ወይም በዚህ በስልክ ያግኙን: +251-936-711812 \nበ AI Mode ትንሽ ቆይተው እንደገና ይሞክሩ"
            )
        else:
            await update.message.reply_text(
                "⚠️ AI MODE is on Maintenance. Please try again in a moment, "
                "Use the /menu options, or call us directly at +251-936-711812."
            )
        record_message() 


##COMMAND HANDLERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    lang = detect_language(update.message.text or "")
    
    keyboard = [
        [InlineKeyboardButton("📋 Services / አገልግሎቶች", callback_data="services")],
        [InlineKeyboardButton("💰 Pricing / ዋጋ", callback_data="pricing")],
        [InlineKeyboardButton("🧪 Lab Tests / የላብ ምርመራ", callback_data="lab_tests")],
        [InlineKeyboardButton("📅 Book Appointment / ቀጠሮ ይያዙ", callback_data="appointment")], 
        [InlineKeyboardButton("📍 Location / አድራሻ", callback_data="location")],
        [InlineKeyboardButton("📞 Contact / አድራሻ", callback_data="contact")],
        [InlineKeyboardButton("❓ FAQ / ተደጋጋሚ ጥያቄዎች", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    greeting = get_greeting(lang)
    if lang == "am":
        help_text = """እንዴት ልረዳዎት እችላለሁ?

• የ ምርመራ መረጃ
• ቀጠሮ መያዝ
• ዋጋ እና ጤና መድን
• የክሊኒኩ አገልግሎቶች

ማንኛውንም ጥያቄ በነጻነት ይጠይቁ!"""
    else:
        help_text = """
• Lab test information
• Book appointments
• Pricing & insurance
• Clinic services

Feel free to ask anything!"""
    
    await update.message.reply_text(
        f"{greeting}\n\n{help_text}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command - show inline keyboard"""
    keyboard = [
        [InlineKeyboardButton("📋 Services / አገልግሎቶች", callback_data="services")],
        [InlineKeyboardButton("💰 Pricing / ዋጋ", callback_data="pricing")],
        [InlineKeyboardButton("🧪 Lab Tests / የላብ ምርመራ", callback_data="lab_tests")],
        [InlineKeyboardButton("📅 Book Appointment / ቀጠሮ ይያዙ", callback_data="appointment")], 
        [InlineKeyboardButton("📍 Location / አድራሻ", callback_data="location")],
        [InlineKeyboardButton("📞 Contact / አድራሻ", callback_data="contact")],
        [InlineKeyboardButton("❓ FAQ / ተደጋጋሚ ጥያቄዎች", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "MediLab Clinic",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear_history - clear user's conversation"""
    user_id = update.effective_user.id
    
    if await clear_conversation(user_id):
        await update.message.reply_text("🧹 Your conversation history has been cleared.")
    else:
        await update.message.reply_text("No conversation history found.") 


##MENU HANDLERS

MENU_OPTIONS = {
    "main": [
        ["🏥 Services", "💰 Pricing"],
        ["🧪 Lab Tests", "📅 Book Appointment"],
        ["📍 Location", "📞 Contact"],
        ["❓ FAQ", "🔄 Clear History"]
    ],
    "services": [
        ["🩺 General Checkup", "❤️ Cardiology"],
        ["👶 Gynecology", "🦴 Orthopedic"],
        ["🔙 Back to Menu"]
    ],
    "lab_tests": [
        ["🩸 Hematology", "🧪 Chemistry"],
        ["🦠 Microbiology", "🧬 Molecular"],
        ["🔙 Back to Menu"]
    ],
    "pricing": [
        ["💰 Consultation", "🧪 Lab Tests"],
        ["📱 Imaging", "🔙 Back to Menu"]
    ]
}

async def show_main_menu(update, context):
    """Show the main menu"""
    keyboard = MENU_OPTIONS["main"]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🏥 MediLab Clinic",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_services_menu(update, context):
    """Show the services sub-menu"""
    keyboard = MENU_OPTIONS["services"]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🏥 **Our Services**\n\nSelect a service for details:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_lab_menu(update, context):
    """Show the lab tests sub-menu"""
    keyboard = MENU_OPTIONS["lab_tests"]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🧪 **Lab Tests**\n\nSelect a test category:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_pricing_menu(update, context):
    """Show the pricing sub-menu"""
    keyboard = MENU_OPTIONS["pricing"]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "💰 **Pricing Information**\n\nSelect a category:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu navigation and actions"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Initialize user menu state if not exists
    if 'menu_state' not in context.user_data:
        context.user_data['menu_state'] = 'main'
    
    current_menu = context.user_data.get('menu_state', 'main')
    
    # Handle back to main menu
    if text == "🔙 Back to Menu":
        context.user_data['menu_state'] = 'main'
        await show_main_menu(update, context)
        return
    
    if current_menu == 'main':
        if text == "🏥 Services":
            context.user_data['menu_state'] = 'services'
            await show_services_menu(update, context)
        elif text == "💰 Pricing":
            context.user_data['menu_state'] = 'pricing'
            await show_pricing_menu(update, context)
        elif text == "🧪 Lab Tests":
            context.user_data['menu_state'] = 'lab_tests'
            await show_lab_menu(update, context)
        elif text == "📅 Book Appointment":
            lang = detect_language(text)
            await handle_appointment_booking(update, context, lang)
        elif text == "📍 Location":
            await update.message.reply_text(get_location_text(), parse_mode='Markdown')
        elif text == "📞 Contact":
            await update.message.reply_text(get_contact_text(), parse_mode='Markdown')
        elif text == "❓ FAQ":
            await update.message.reply_text(get_faq_text(), parse_mode='Markdown')
        elif text == "🔄 Clear History":
            if await clear_conversation(user_id):
                await update.message.reply_text("🧹 Your conversation history has been cleared.")
            else:
                await update.message.reply_text("No conversation history found.")
    
    # Handle sub-menu selections
    elif current_menu == 'services':
        if text == "🩺 General Checkup":
            await update.message.reply_text("🩺 **General Checkup**\n\nPrice: 300-500 ETB\nDuration: 30 mins\nWalk-in available, no appointment needed.", parse_mode='Markdown')
        elif text == "❤️ Cardiology":
            await update.message.reply_text("❤️ **Cardiology Services**\n\nPrice: 600-1,200 ETB\nPlease book in advance.\nCall: +251-936-711812", parse_mode='Markdown')
        elif text == "👶 Gynecology":
            await update.message.reply_text("👶 **Gynecology Services**\n\nPrice: 600-1,200 ETB\nAvailable Mon-Sat, 8AM-8PM", parse_mode='Markdown')
        elif text == "🦴 Orthopedic":
            await update.message.reply_text("🦴 **Orthopedic Services**\n\nPrice: 600-1,200 ETB\nSpecialist available Tue & Thu", parse_mode='Markdown')
    
    elif current_menu == 'lab_tests':
        if text == "🩸 Hematology":
            await update.message.reply_text(get_lab_hematology(), parse_mode='Markdown')
        elif text == "🧪 Chemistry":
            await update.message.reply_text(get_lab_chemistry(), parse_mode='Markdown')
        elif text == "🦠 Microbiology":
            await update.message.reply_text(get_lab_microbiology(), parse_mode='Markdown')
        elif text == "🧬 Molecular":
            await update.message.reply_text(get_lab_molecular(), parse_mode='Markdown')
    
    elif current_menu == 'pricing':
        if text == "💰 Consultation":
            await update.message.reply_text("💰 **Consultation Prices**\n\n• General Practitioner: 300-500 ETB\n• Specialist: 600-1,200 ETB\n• Teleconsultation: 400-800 ETB", parse_mode='Markdown')
        elif text == "🧪 Lab Tests":
            await update.message.reply_text("💰 **Lab Test Prices**\n\n• Basic Panel: 200-500 ETB\n• Comprehensive: 500-1,500 ETB\n• Specialized: 1,500-3,000 ETB\n\n10% senior discount available.", parse_mode='Markdown')
        elif text == "📱 Imaging":
            await update.message.reply_text("💰 **Imaging Prices**\n\n• X-ray: 400-800 ETB\n• Ultrasound: 800-1,500 ETB\n• CT Scan: 5,000+ ETB (referral required)", parse_mode='Markdown')


##CLLBACK HANDLER
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    lang = detect_language(data)
    
    # ====== MAIN MENU ======
    if data == "back":
        await start(update, context)
        return
    
    if data == "services":
        text = get_services_text()
        await query.edit_message_text(text, parse_mode='Markdown')
        return
    
    if data == "pricing":
        text = get_pricing_text()
        await query.edit_message_text(text, parse_mode='Markdown')
        return
    
    if data == "lab_tests":
        keyboard = [
            [InlineKeyboardButton("🩸 Hematology", callback_data="lab_hematology")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="lab_chemistry")],
            [InlineKeyboardButton("🦠 Microbiology", callback_data="lab_microbiology")],
            [InlineKeyboardButton("🧬 Molecular (GeneXpert)", callback_data="lab_molecular")],
            [InlineKeyboardButton("🩹 Serology/Immunology", callback_data="lab_serology")],
            [InlineKeyboardButton("🔬 Parasitology", callback_data="lab_parasitology")],
            [InlineKeyboardButton("💉 Blood Bank", callback_data="lab_bloodbank")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🧪 **Select Lab Test Category**\n\nChoose a category:"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # ====== LAB SUB-CATEGORIES ======
    if data == "lab_hematology":
        text = get_lab_hematology()
    elif data == "lab_chemistry":
        text = get_lab_chemistry()
    elif data == "lab_microbiology":
        text = get_lab_microbiology()
    elif data == "lab_molecular":
        text = get_lab_molecular()
    elif data == "lab_serology":
        text = get_lab_serology()
    elif data == "lab_parasitology":
        text = get_lab_parasitology()
    elif data == "lab_bloodbank":
        text = get_lab_bloodbank()
    
    # ====== LOCATION, CONTACT, FAQ ======
    elif data == "location":
        text = get_location_text()
    elif data == "contact":
        text = get_contact_text()
    elif data == "faq":
        text = get_faq_text()
    
    # ====== APPOINTMENT ======
    elif data.startswith("appt_") or data == "appointment":
        await handle_appointment_callback(update, context, query, user_id)
        return
    
    # Edit message with response
    if data not in ["lab_tests", "appointment"] and not data.startswith("appt_"):
        await query.edit_message_text(text, parse_mode='Markdown') 


##APPOINTMENT HANDLERS
 
async def handle_appointment_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, lang="en"):
    """Handle appointment booking flow"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if lang == "am":
        text = "📅 **ቀጠሮ መያዝ**\n\nእባክዎን አንዱን ይምረጡ:"
    else:
        text = "📅 **Book an Appointment**\n\nPlease select:"
    
    keyboard = get_appointment_keyboard("service_select")
    await set_appointment(user_id, {"step": "service_select"}, username=username)
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def handle_appointment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query, user_id):
    """Handle appointment-related button callbacks"""
    data = query.data
    lang = detect_language(data)
    
    if data == "appointment":
        await handle_appointment_booking_callback(update, context, lang)
        return
    
    if data.startswith("appt_"):
        service = data.replace("appt_", "")
        
        if service == "call":
            text = "📞 **Call us to book:**\n+251-936-711812\n+251-115-789012\n\nMon-Sat, 8AM-8PM"
            await query.edit_message_text(text, parse_mode='Markdown')
            return
        
        service_name = get_service_name(service)
        await set_appointment(user_id, {
            "step": "date_select",
            "service": service_name
        })
        
        keyboard = get_appointment_keyboard("date_select", service)
        text = f"📅 **Book {service_name} Appointment**\n\nWhen would you like to come?"
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return
    
    if data.startswith("appt_date_"):
        parts = data.split("_")
        when = parts[2]
        service = parts[3] if len(parts) > 3 else "general"
        service_name = get_service_name(service)
        
        if when == "today":
            date_str = get_date_today()
        elif when == "tomorrow":
            date_str = get_date_tomorrow()
        else:
            text = f"📅 **{service_name} Appointment**\n\nPlease reply with your preferred date (e.g., 2026-08-20)\n\nOr call us: +251-936-711812"
            await query.edit_message_text(text, parse_mode='Markdown')
            await set_appointment(user_id, {
                "step": "waiting_date",
                "service": service_name
            })
            return
        
        await set_appointment(user_id, {
            "step": "time_select",
            "service": service_name,
            "date": date_str
        })
        
        keyboard = get_appointment_keyboard("time_select", service)
        text = f"📅 **{service_name} Appointment**\nDate: {date_str}\n\nSelect a time:"
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return
    
    if data.startswith("appt_time_"):
        parts = data.split("_")
        time_slot = parts[2]
        service = parts[3] if len(parts) > 3 else "general"
        service_name = get_service_name(service)
        time_formatted = format_time(time_slot)
        
        appt_data = await get_appointment(user_id) or {}
        date_str = appt_data.get("date", "today")
        
        keyboard = get_appointment_confirmation_keyboard(service)
        await set_appointment(user_id, {
            "step": "confirm",
            "service": service_name,
            "date": date_str,
            "time": time_formatted
        })
        
        text = get_confirmation_text(service_name, date_str, time_formatted)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return
    
    if data.startswith("appt_confirm_"):
        # confirm_appointment atomically moves the working row into
        # permanent history (appointment_history table) and clears it -
        # this is what actually makes the booking durable. Previously the
        # data was just dropped from an in-memory dict with nothing
        # written anywhere else, so confirmed bookings could vanish
        # before staff ever saw them.
        confirmed = await confirm_appointment(user_id)
        if not confirmed:
            await query.edit_message_text(
                "⚠️ We couldn't find your booking details - please start over with /menu.",
                parse_mode='Markdown'
            )
            return
        
        service_name = confirmed.get("service") or "General"
        date_str = confirmed.get("date") or "today"
        time_formatted = confirmed.get("time") or "TBD"
        username = update.effective_user.username or "Unknown"
        
        text = get_confirmed_text(service_name, date_str, time_formatted)
        
        await query.edit_message_text(text, parse_mode='Markdown')
        await update.effective_chat.send_message(
            "📋 Your appointment has been booked! We'll send you a reminder soon."
        )
        await notify_admin_of_booking(
            context.bot, username, service_name, date_str, time_formatted, user_id
        )
        return

async def handle_appointment_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang="en"):
    """Handle appointment booking from callback"""
    query = update.callback_query
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if lang == "am":
        text = "📅 **ቀጠሮ መያዝ**\n\nእባክዎን አንዱን ይምረጡ:"
    else:
        text = "📅 **Book an Appointment**\n\nPlease select:"
    
    keyboard = get_appointment_keyboard("service_select")
    await set_appointment(user_id, {"step": "service_select"}, username=username)
    
    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
