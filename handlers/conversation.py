from telegram import Update
from telegram.ext import ContextTypes
from database.db import AsyncSessionLocal
from services.order_service import (
    get_or_create_customer,
    update_customer_details,
    create_order,
    has_open_order,
)
from services.ai_service import generate_ai_response
from services.payment_service import create_payment_submission
from config.catalogue import VIP_CARDS, SERVICES
from utils.payment_text import format_both_payment_options
from config.settings import settings


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = (
        "Welcome to Celebrity Management. How may I assist you today?\n\n"
        "We offer exclusive VIP membership cards and premium services:\n\n"
        "VIP Cards:\n"
        "• Bronze VIP — $250\n"
        "• Silver VIP — $750\n"
        "• Gold VIP — $1,500\n"
        "• Platinum VIP — $3,500\n"
        "• Diamond VIP — $7,500\n\n"
        "Services:\n"
        "• Meet & Greet — $2,500\n"
        "• Vacation Experience — $5,000\n\n"
        "Please let me know which option interests you, or if you have any questions.\n\n"
        "Celebrity Management Team"
    )
    await update.message.reply_text(greeting)

    try:
        user = update.effective_user
        context.user_data.clear()
        async with AsyncSessionLocal() as session:
            await get_or_create_customer(session, user.id, user.first_name)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"DB error in /start: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()

    async with AsyncSessionLocal() as session:
        customer = await get_or_create_customer(session, user.id, user.first_name)

        if context.user_data.get("collecting_order"):
            await _handle_order_collection(update, context, session, customer, text)
            return

        lower = text.lower()

        if any(k in lower for k in ["buy", "purchase", "order", "get the", "i want", "i'd like"]):
            selected = _detect_item(lower)
            if selected:
                item_type, item_key = selected
                if await has_open_order(session, customer.id):
                    await update.message.reply_text(
                        "You already have an open order. Please complete payment or contact support "
                        "before placing a new order.\n\nCelebrity Management Team"
                    )
                    return

                context.user_data["collecting_order"] = True
                context.user_data["item_type"] = item_type
                context.user_data["item_key"] = item_key
                context.user_data["step"] = "full_name"

                item_name = (
                    VIP_CARDS[item_key]["name"] if item_type == "vip_card"
                    else SERVICES[item_key]["name"]
                )
                await update.message.reply_text(
                    f"Excellent choice. You have selected the {item_name}.\n\n"
                    "To proceed, please provide your Full Name."
                )
                return

        reply = await generate_ai_response(session, customer, text)
        await update.message.reply_text(reply)


def _detect_item(text: str):
    text = text.lower()
    if "bronze" in text:
        return "vip_card", "bronze"
    if "silver" in text:
        return "vip_card", "silver"
    if "gold" in text and "vip" in text:
        return "vip_card", "gold"
    if "platinum" in text:
        return "vip_card", "platinum"
    if "diamond" in text:
        return "vip_card", "diamond"
    if "meet" in text and "greet" in text:
        return "service", "meet_greet"
    if "vacation" in text:
        return "service", "vacation"
    return None


async def _handle_order_collection(update, context, session, customer, text):
    step = context.user_data.get("step")

    if step == "full_name":
        context.user_data["full_name"] = text
        context.user_data["step"] = "email"
        await update.message.reply_text("Thank you. Please provide your Email Address.")
        return

    if step == "email":
        if "@" not in text or "." not in text:
            await update.message.reply_text(
                "That does not appear to be a valid email address. Please provide a correct Email Address."
            )
            return
        context.user_data["email"] = text
        context.user_data["step"] = "country"
        await update.message.reply_text("Thank you. Please provide your Country.")
        return

    if step == "country":
        full_name = context.user_data["full_name"]
        email = context.user_data["email"]
        country = text

        await update_customer_details(session, customer.telegram_id, full_name, email, country)

        item_type = context.user_data["item_type"]
        item_key = context.user_data["item_key"]

        order, error = await create_order(session, customer, item_type, item_key)
        if error:
            await update.message.reply_text(error + "\n\nCelebrity Management Team")
            context.user_data.clear()
            return

        context.user_data.clear()

        payment_text = format_both_payment_options()
        msg = (
            f"Your order has been created successfully.\n\n"
            f"Order ID: {order.order_id}\n"
            f"Item: {order.item_name}\n"
            f"Amount: ${order.price:,.0f} {order.currency}\n\n"
            f"{payment_text}\n\n"
            "Celebrity Management Team"
        )
        await update.message.reply_text(msg)

        try:
            admin_msg = (
                f"🆕 New Order Created\n\n"
                f"Order ID: {order.order_id}\n"
                f"Customer: {full_name}\n"
                f"Email: {email}\n"
                f"Country: {country}\n"
                f"Telegram ID: {customer.telegram_id}\n"
                f"Item: {order.item_name}\n"
                f"Amount: ${order.price:,.0f}"
            )
            await context.bot.send_message(chat_id=settings.admin_telegram_id, text=admin_msg)
        except Exception as e:
            print(f"Failed to notify admin: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file_id = photo.file_id

    async with AsyncSessionLocal() as session:
        customer = await get_or_create_customer(session, user.id, user.first_name)

        from sqlalchemy import select, and_
        from database.models import Order, OrderStatus

        result = await session.execute(
            select(Order).where(
                and_(
                    Order.customer_id == customer.id,
                    Order.status.in_([
                        OrderStatus.PENDING_PAYMENT.value,
                        OrderStatus.NEEDS_MORE_INFO.value,
                    ])
                )
            ).order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if not order:
            await update.message.reply_text(
                "I could not find an open order that is awaiting payment. "
                "If you believe this is an error, please open a support request.\n\n"
                "Celebrity Management Team"
            )
            return

        payment = await create_payment_submission(
            session,
            order,
            screenshot_file_id=file_id,
            extracted_info="Screenshot received – pending manual verification by administrator.",
        )

        await update.message.reply_text(
            "Thank you. Your payment screenshot has been received and is now Pending Verification. "
            "Our team will review it and notify you once a decision has been made.\n\n"
            "Celebrity Management Team"
        )

        try:
            admin_msg = (
                f"📸 New Payment Screenshot\n\n"
                f"Order ID: {order.order_id}\n"
                f"Customer: {customer.full_name or customer.first_name}\n"
                f"Telegram ID: {customer.telegram_id}\n"
                f"Amount: ${order.price:,.0f}\n"
                f"Payment ID: {payment.id}"
            )
            await context.bot.send_message(
                chat_id=settings.admin_telegram_id,
                text=admin_msg,
            )
            await context.bot.send_photo(
                chat_id=settings.admin_telegram_id,
                photo=file_id,
                caption=f"Screenshot for Order {order.order_id} / Payment {payment.id}"
            )
        except Exception as e:
            print(f"Failed to notify admin of screenshot: {e}")
