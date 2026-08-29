import logging
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config.settings import settings
from database.db import init_db
from handlers.conversation import start, handle_message, handle_photo
from handlers.admin import (
    admin_help,
    list_orders,
    list_pending,
    verify_payment,
    reject_payment,
    needs_info,
    view_order,
    list_tickets,
    reply_ticket,
    close_ticket_cmd,
    list_customers,
    show_catalogue,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await init_db()
    logger.info("Database initialised.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    logger.error(traceback.format_exc())
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "I apologise — a temporary technical issue occurred. "
                "Please try again in a moment.\n\nCelebrity Management Team"
            )
        except Exception:
            pass


def main():
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", admin_help))
    application.add_handler(CommandHandler("orders", list_orders))
    application.add_handler(CommandHandler("pending", list_pending))
    application.add_handler(CommandHandler("verify", verify_payment))
    application.add_handler(CommandHandler("reject", reject_payment))
    application.add_handler(CommandHandler("needsinfo", needs_info))
    application.add_handler(CommandHandler("order", view_order))
    application.add_handler(CommandHandler("tickets", list_tickets))
    application.add_handler(CommandHandler("reply", reply_ticket))
    application.add_handler(CommandHandler("close", close_ticket_cmd))
    application.add_handler(CommandHandler("customers", list_customers))
    application.add_handler(CommandHandler("catalogue", show_catalogue))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))

    logger.info("Celebrity Management Bot starting...")
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
