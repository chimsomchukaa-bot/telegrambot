from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Order, Payment, Customer, PaymentStatus
from services.payment_service import update_payment_status, get_pending_payments
from services.support_service import get_open_tickets, get_ticket_by_id, add_support_message, close_ticket
from services.order_service import get_order_by_order_id
from config.settings import settings
from config.catalogue import VIP_CARDS, SERVICES


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != settings.admin_telegram_id:
            await update.message.reply_text("Access denied.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🔐 *Administrator Commands*

/orders – List recent orders
/pending – List payments awaiting verification
/verify <payment_id> – Mark payment as Verified
/reject <payment_id> [note] – Mark payment as Rejected
/needsinfo <payment_id> [note] – Mark as Needs More Info
/order <CM-YYYY-XXXX> – View specific order
/tickets – List open support tickets
/reply <ticket_id> <message> – Reply to a support ticket
/close <ticket_id> – Close a support ticket
/customers – List recent customers
/catalogue – Show current VIP cards & services
/help – This message
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


@admin_only
async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(15)
        )
        orders = list(result.scalars().all())
        if not orders:
            await update.message.reply_text("No orders found.")
            return
        lines = ["📋 *Recent Orders*\n"]
        for o in orders:
            lines.append(f"`{o.order_id}` | {o.item_name} | ${o.price:,.0f} | *{o.status}*")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@admin_only
async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        payments = await get_pending_payments(session)
        if not payments:
            await update.message.reply_text("No payments currently pending verification.")
            return
        lines = ["⏳ *Pending Payment Verifications*\n"]
        for p in payments:
            order_result = await session.execute(select(Order).where(Order.id == p.order_id))
            order = order_result.scalar_one()
            lines.append(
                f"Payment ID: `{p.id}`\n"
                f"Order: `{order.order_id}` | {order.item_name} | ${order.price:,.0f}\n"
                f"Submitted: {p.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@admin_only
async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /verify <payment_id>")
        return
    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Payment ID must be a number.")
        return
    async with AsyncSessionLocal() as session:
        payment = await update_payment_status(
            session, payment_id, PaymentStatus.VERIFIED.value, "Verified by administrator"
        )
        if not payment:
            await update.message.reply_text("Payment not found.")
            return
        order_result = await session.execute(select(Order).where(Order.id == payment.order_id))
        order = order_result.scalar_one()
        customer_result = await session.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = customer_result.scalar_one()
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_id,
                text=(
                    f"Your payment for Order {order.order_id} ({order.item_name}) "
                    f"has been *Verified*.\n\n"
                    "Thank you for your payment. Our team will be in contact regarding next steps.\n\n"
                    "Celebrity Management Team"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Could not notify customer: {e}")
        await update.message.reply_text(
            f"✅ Payment {payment_id} marked as *Verified*. Customer has been notified.",
            parse_mode="Markdown",
        )


@admin_only
async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /reject <payment_id> [optional note]")
        return
    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Payment ID must be a number.")
        return
    note = " ".join(context.args[1:]) if len(context.args) > 1 else "Payment rejected by administrator."
    async with AsyncSessionLocal() as session:
        payment = await update_payment_status(session, payment_id, PaymentStatus.REJECTED.value, note)
        if not payment:
            await update.message.reply_text("Payment not found.")
            return
        order_result = await session.execute(select(Order).where(Order.id == payment.order_id))
        order = order_result.scalar_one()
        customer_result = await session.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = customer_result.scalar_one()
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_id,
                text=(
                    f"Your payment for Order {order.order_id} has been *Rejected*.\n\n"
                    f"Reason: {note}\n\n"
                    "Please contact support if you need assistance.\n\n"
                    "Celebrity Management Team"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Could not notify customer: {e}")
        await update.message.reply_text(
            f"❌ Payment {payment_id} marked as *Rejected*. Customer notified.",
            parse_mode="Markdown",
        )


@admin_only
async def needs_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /needsinfo <payment_id> [optional note]")
        return
    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Payment ID must be a number.")
        return
    note = " ".join(context.args[1:]) if len(context.args) > 1 else "Additional information required."
    async with AsyncSessionLocal() as session:
        payment = await update_payment_status(
            session, payment_id, PaymentStatus.NEEDS_MORE_INFO.value, note
        )
        if not payment:
            await update.message.reply_text("Payment not found.")
            return
        order_result = await session.execute(select(Order).where(Order.id == payment.order_id))
        order = order_result.scalar_one()
        customer_result = await session.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = customer_result.scalar_one()
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_id,
                text=(
                    f"Regarding your payment for Order {order.order_id}:\n\n"
                    f"We require additional information.\n\n"
                    f"{note}\n\n"
                    "Please reply with the requested details or a clearer screenshot.\n\n"
                    "Celebrity Management Team"
                ),
            )
        except Exception as e:
            print(f"Could not notify customer: {e}")
        await update.message.reply_text(
            f"ℹ️ Payment {payment_id} marked as *Needs More Info*. Customer notified.",
            parse_mode="Markdown",
        )


@admin_only
async def view_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /order <CM-YYYY-XXXX>")
        return
    order_id = context.args[0].upper()
    async with AsyncSessionLocal() as session:
        order = await get_order_by_order_id(session, order_id)
        if not order:
            await update.message.reply_text("Order not found.")
            return
        customer_result = await session.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = customer_result.scalar_one()
        text = (
            f"*Order {order.order_id}*\n\n"
            f"Item: {order.item_name}\n"
            f"Price: ${order.price:,.0f} {order.currency}\n"
            f"Status: *{order.status}*\n"
            f"Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"*Customer*\n"
            f"Name: {customer.full_name or 'N/A'}\n"
            f"Email: {customer.email or 'N/A'}\n"
            f"Country: {customer.country or 'N/A'}\n"
            f"Telegram ID: `{customer.telegram_id}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def list_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        tickets = await get_open_tickets(session)
        if not tickets:
            await update.message.reply_text("No open support tickets.")
            return
        lines = ["🎫 *Open Support Tickets*\n"]
        for t in tickets:
            lines.append(f"`{t.ticket_id}` | {t.category} | {t.subject or ''}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@admin_only
async def reply_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply <ticket_id> <message>")
        return
    ticket_id = context.args[0].upper()
    message = " ".join(context.args[1:])
    async with AsyncSessionLocal() as session:
        ticket = await get_ticket_by_id(session, ticket_id)
        if not ticket:
            await update.message.reply_text("Ticket not found.")
            return
        await add_support_message(session, ticket, "admin", message)
        customer_result = await session.execute(select(Customer).where(Customer.id == ticket.customer_id))
        customer = customer_result.scalar_one()
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_id,
                text=(
                    f"Reply regarding your support request ({ticket.ticket_id}):\n\n"
                    f"{message}\n\n"
                    "Celebrity Management Team"
                ),
            )
        except Exception as e:
            print(f"Could not deliver support reply: {e}")
        await update.message.reply_text(f"Reply sent to ticket {ticket_id}.")


@admin_only
async def close_ticket_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /close <ticket_id>")
        return
    ticket_id = context.args[0].upper()
    async with AsyncSessionLocal() as session:
        ticket = await get_ticket_by_id(session, ticket_id)
        if not ticket:
            await update.message.reply_text("Ticket not found.")
            return
        await close_ticket(session, ticket)
        customer_result = await session.execute(select(Customer).where(Customer.id == ticket.customer_id))
        customer = customer_result.scalar_one()
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_id,
                text=(
                    f"Your support request ({ticket.ticket_id}) has been closed.\n\n"
                    "If you need further assistance, you may open a new request.\n\n"
                    "Celebrity Management Team"
                ),
            )
        except Exception:
            pass
        await update.message.reply_text(f"Ticket {ticket_id} closed.")


@admin_only
async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Customer).order_by(Customer.created_at.desc()).limit(20)
        )
        customers = list(result.scalars().all())
        if not customers:
            await update.message.reply_text("No customers yet.")
            return
        lines = ["👥 *Recent Customers*\n"]
        for c in customers:
            lines.append(
                f"`{c.telegram_id}` | {c.full_name or c.first_name or 'N/A'} | {c.email or '—'}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@admin_only
async def show_catalogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📦 *Current Catalogue*\n\n*VIP Cards*\n"]
    for key, card in VIP_CARDS.items():
        lines.append(f"• {card['name']} — ${card['price']:,}")
    lines.append("\n*Services*")
    for key, svc in SERVICES.items():
        lines.append(f"• {svc['name']} — ${svc['price']:,}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
