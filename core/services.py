##APPOINTMENT
import time
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_CHAT_ID

logger = logging.getLogger("mediassistant")


async def notify_admin_of_booking(bot, username, service_name, date_str, time_formatted, user_id):
    """Ping clinic staff when a patient confirms a booking.

    Confirmed appointments are always persisted to the database regardless
    of whether this succeeds (see core/db.py) — this is a best-effort
    convenience notification, not the system of record.
    """
    if not ADMIN_CHAT_ID:
        return
    text = (
        f"📥 New appointment confirmed\n"
        f"Patient: @{username} (id: {user_id})\n"
        f"Service: {service_name}\n"
        f"Date: {date_str}\n"
        f"Time: {time_formatted}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    except Exception as e:
        logger.warning("Failed to notify admin chat of new booking: %s", e)

def get_service_name(service_key):
    """Get display name for a service"""
    service_names = {
        "general": "General Checkup",
        "lab": "Lab Test Only",
        "cardio": "Cardiology",
        "gyn": "Gynecology",
        "ortho": "Orthopedic"
    }
    return service_names.get(service_key, "General")

def get_appointment_keyboard(step="service_select", service=None):
    """Get keyboard for appointment flow"""
    if step == "service_select":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🩺 General Checkup", callback_data="appt_general")],
            [InlineKeyboardButton("🧪 Lab Test Only", callback_data="appt_lab")],
            [InlineKeyboardButton("❤️ Cardiology", callback_data="appt_cardio")],
            [InlineKeyboardButton("👶 Gynecology", callback_data="appt_gyn")],
            [InlineKeyboardButton("🦴 Orthopedic", callback_data="appt_ortho")],
            [InlineKeyboardButton("📞 Call to Book", callback_data="appt_call")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    
    elif step == "date_select":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Today", callback_data=f"appt_date_today_{service}")],
            [InlineKeyboardButton("📅 Tomorrow", callback_data=f"appt_date_tomorrow_{service}")],
            [InlineKeyboardButton("📅 Pick a date", callback_data=f"appt_date_pick_{service}")],
            [InlineKeyboardButton("🔙 Back", callback_data="appointment")]
        ])
    
    elif step == "time_select":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🕐 9:00 AM", callback_data=f"appt_time_0900_{service}")],
            [InlineKeyboardButton("🕐 10:00 AM", callback_data=f"appt_time_1000_{service}")],
            [InlineKeyboardButton("🕐 11:00 AM", callback_data=f"appt_time_1100_{service}")],
            [InlineKeyboardButton("🕐 2:00 PM", callback_data=f"appt_time_1400_{service}")],
            [InlineKeyboardButton("🕐 3:00 PM", callback_data=f"appt_time_1500_{service}")],
            [InlineKeyboardButton("🕐 4:00 PM", callback_data=f"appt_time_1600_{service}")],
            [InlineKeyboardButton("🔙 Back", callback_data="appointment")]
        ])
    
    return None

def get_appointment_confirmation_keyboard(service):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data=f"appt_confirm_{service}")],
        [InlineKeyboardButton("🔄 Change", callback_data="appointment")],
        [InlineKeyboardButton("❌ Cancel", callback_data="back")]
    ])

def format_time(time_slot):
    """Format time string for display"""
    time_formatted = f"{time_slot[:2]}:{time_slot[2:]}"
    if int(time_slot[:2]) < 12:
        time_formatted += " AM"
    else:
        pm_hour = int(time_slot[:2]) - 12
        time_formatted = f"{pm_hour:02d}:{time_slot[2:]} PM"
    return time_formatted

def get_confirmation_text(service_name, date_str, time_formatted):
    return f"""📋 **Confirm Appointment**

**Service:** {service_name}
**Date:** {date_str}
**Time:** {time_formatted}

✅ Please confirm or change:"""

def get_confirmed_text(service_name, date_str, time_formatted):
    return f"""✅ **Appointment Confirmed!**

**Service:** {service_name}
**Date:** {date_str}
**Time:** {time_formatted}

📍 **Location:** MediLab Clinic, Bole Sub-city, near Bole Medhanialem Church

📞 **Questions?** Call us: +251-936-711812

⚠️ Please arrive 15 minutes early.

*We look forward to seeing you!*"""

def get_date_today():
    return time.strftime("%Y-%m-%d")

def get_date_tomorrow():
    return time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400)) 



##LAB INFO 
def get_lab_hematology():
    return """🩸 **Hematology Tests / የደም ምርመራ**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| CBC | ~550 | 1 hrs |
| ESR | ~200 | 1 hr |
| Coagulation (PT/PTT) | ~400 | 2 hrs |
| Peripheral Smear | ~250 | 2 hrs |

📋 **Prep:** No fasting required
⏰ **Walk-in:** Until 7 PM
ጤና መድን ይቻላል"""

def get_lab_chemistry():
    return """🧪 **Clinical Chemistry Tests**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| LFT | ~500 | 30 min |
| RFT | ~450 | 30 min |
| Lipid Profile | ~500 | 30 min |
| Fasting Glucose | ~200 | 30 min |
| Electrolytes | ~400 | 2 hrs |
| Cardiac Enzymes | ~600 | 4 hrs |

📋 **Prep:** Fasting 8-12 hrs for glucose/lipid
⏰ **Walk-in:** Until 7 PM"""

def get_lab_microbiology():
    return """🦠 **Microbiology Tests**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| Culture & Sensitivity | ~800 | 3-5 days |
| Gram Stain | ~300 | 2 hrs |
| AFB (TB) | ~500 | 3 days |
| Fungal Culture | ~600 | 5-7 days |

📋 **Prep:** Bring samples on-site
⏰ **Sample collection:** Until 6 PM"""

def get_lab_molecular():
    return """🧬 **Molecular Tests (GeneXpert)**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| GeneXpert TB | ~1,200 | 4 hrs |
| GeneXpert COVID | ~1,000 | 2 hrs |
| PCR (limited) | ~2,000 | 24 hrs |

📋 **Prep:** Bring doctor's order
⏰ **Walk-in:** Until 6 PM
ጤና መድን ይቻላል"""

def get_lab_serology():
    return """🩹 **Serology / Immunology Tests**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| HIV Rapid | ~200 | 30 mins |
| HIV ELISA | ~400 | 4 hrs |
| HBV/HCV | ~350 each | 30 min |
| Syphilis (RPR) | ~250 | 2 hrs |
| Widal (Typhoid) | ~250 | 2 hrs |
| Brucella | ~300 | 4 hrs |
| RA Factor | ~300 | 4 hrs |

📋 **Prep:** No fasting required
⏰ **Walk-in:** Until 7 PM"""

def get_lab_parasitology():
    return """🔬 **Parasitology Tests**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| Stool O&P | ~200 | 2 hrs |
| Malaria Smear | ~150 | 30 mins |
| Blood Film (thick/thin) | ~200 | 1 hr |
| Filaria | ~250 | 2 hrs |

📋 **Prep:** No fasting required
⏰ **Walk-in:** Until 7 PM"""

def get_lab_bloodbank():
    return """💉 **Blood Bank Services**

| Test | Price (ETB) | TAT |
|------|-------------|-----|
| ABO/Rh Grouping | ~180 | 30 mins |
| Cross-matching | ~300 | 1 hr |
| Coombs Test (Direct) | ~250 | 2 hrs |
| Coombs Test (Indirect) | ~300 | 2 hrs |

📋 **Prep:** No fasting required
⏰ **Walk-in:** Until 7 PM
⚠️ **Note:** Blood donation services available""" 

##CLINIC DATA 
# Clinic services, pricing, lab info, location, contact, FAQ

def get_services_text():
    return """🏥 **Our Services / አገልግሎቶች**

**Laboratory / የላብራቶሪ:**
• Hematology (CBC, ESR, coagulation)
• Chemistry (LFT, RFT, lipids, glucose)
• Microbiology (culture, sensitivity)
• Parasitology (stool, blood films)
• Serology (HIV, HBV, HCV, syphilis)
• Molecular (GeneXpert TB/COVID)
• Blood bank (grouping, cross-match)

**Clinical / ክሊኒካል:**
• General medicine (adult/peds)
• Cardiology, Gyn/OB, Ortho, Derm
• Minor emergency care
• Pharmacy
• Teleconsultation

📅 Walk-in or book online: LabH.pythonanywhere.com/patient_portal"""

def get_pricing_text():
    return """💰 **Price Ranges / የዋጋ መጠን** (ETB)

**Consultation / ምክር:**
• GP: 300 - 500
• Specialist: 600 - 1,200

**Lab Tests / የላብ ምርመራ:**
• CBC: ~550
• Chemistry panel: 450 - 600
• Lipid profile: ~500
• HIV rapid: ~200
• GeneXpert TB: ~1,200
• Malaria smear: ~150
• Widal: ~250

**Imaging / ምስል:**
• X-ray: 400 - 800
• Ultrasound: 800 - 1,500
 
📱 Pay via Telebirr, cash, or card
🎯 10% senior discount | 15% chronic care plans"""

def get_location_text():
    return """📍 **Location / አድራሻ**

**MediLab Clinic**
Bole Sub-city, Woreda 03
Near Bole Medhanialem Church
Addis Ababa, Ethiopia

**Hours / የስራ ሰዓት:** Mon-Sat, 8AM - 8PM

📞 +251-936-711812 / +251-703702129
✉️ labh.pythonanywhere.com"""

def get_contact_text():
    return """📞 **Contact Us / ያግኙን**

**Phone / ስልክ:**
• +251-936-711812
• +251-703702129

**Email / ኢሜይል:**
• indexazacc@gmail.com

**Social Media:**
• Telegram: @DigitalAutomotions
• Facebook: 

**Emergency:** Call us immediately for urgent concerns.
**Appointments:** LabH.pythonanywhere.com/patient_portal"""

def get_faq_text():
    # NOTE: verify the local emergency number with the clinic before
    # deploying — this was hardcoded as "911" (a US number, wrong for
    # Ethiopia) in the original version. Confirm the correct number for
    # your city/region.
    return """❓ **FAQ / ተደጋጋሚ ጥያቄዎች**

**Q: Do I need a referral?**
A: No, walk-ins are welcome for most services.

**Q: What are your hours?**
A: Monday-Saturday, 8AM - 8PM.

**Q: How long for lab results?**
A: 30 mins to 72 hours depending on test.

**Q: Do you accept insurance?**
A: Not Yet, But for the future..

**Q: Can I pay with Telebirr?**
A: Yes, Telebirr is accepted.

**Q: Do you see emergencies?**
A: For minor emergencies during hours. For major emergencies, call the national emergency line (907) or go to the nearest hospital immediately.

📞 More questions? Call +251-936-711812"""
