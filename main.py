import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from .env before config.py reads it

from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import BOT_TOKEN, WEB_PORT
from core.handlers import start, callback_menu, clear_history, handle_message, menu_handler, MENU_OPTIONS, button_callback
from core.web import setup_web_server
from core.storage import init_schema, housekeeping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mediassistant")


async def housekeeping_loop():
    """Periodic cleanup task.

    This replaced a job that wiped ALL conversations and ALL in-progress
    appointments from memory every hour - which meant a patient's
    half-finished (or even just-confirmed) booking could disappear before
    staff ever saw it, and every restart lost everything. Now: confirmed
    appointments live permanently in the database and are never touched
    here; this only prunes old conversation logs and booking flows the
    patient abandoned and never finished.
    """
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            pruned = await housekeeping()
            logger.info("Housekeeping: pruned %s abandoned booking flow(s)", pruned)
        except Exception:
            logger.exception("Housekeeping run failed")


async def main():
    await init_schema()

    # Build the bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("restart", start))
    application.add_handler(CommandHandler("clear_history", clear_history))
    application.add_handler(CommandHandler("menu", callback_menu))

    #  menu handler - catches exact menu button text
    menu_patterns = list({item for sublist in MENU_OPTIONS.values() for row in sublist for item in row})
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f"^({'|'.join(menu_patterns)})$"),
        menu_handler
    ))

    #  AI message handler - catches everything else
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    #  callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("Clinic Bot is running with multilingual support!")

    # Start housekeeping (non-destructive - see docstring above)
    asyncio.create_task(housekeeping_loop())

    # Setup web dashboard
    web_app = setup_web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', WEB_PORT).start()
    logger.info("Dashboard: http://0.0.0.0:%s", WEB_PORT)

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
