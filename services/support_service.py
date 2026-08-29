
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import SupportTicket, SupportMessage, Customer, SupportStatus
import pytz


async def generate_ticket_id(session: AsyncSession) -> str:
    year = datetime.now(pytz.timezone("America/New_York")).year
    prefix = f"ST-{year}-"
    result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.ticket_id.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    return f"{prefix}{count + 1:04d}"


async def create_support_ticket(
    session: AsyncSession,
    customer: Customer,
    category: str,
    initial_message: str,
    subject: str = "",
) -> SupportTicket:
    ticket_id = await generate_ticket_id(session)
    ticket = SupportTicket(
        ticket_id=ticket_id,
        customer_id=customer.id,
        category=category,
        subject=subject or category,
        status=SupportStatus.OPEN.value,
    )
    session.add(ticket)
    await session.flush()

    msg = SupportMessage(
        ticket_id=ticket.id,
        sender_type="customer",
        message=initial_message,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def add_support_message(
    session: AsyncSession,
    ticket: SupportTicket,
    sender_type: str,
    message: str,
) -> SupportMessage:
    msg = SupportMessage(
        ticket_id=ticket.id,
        sender_type=sender_type,
        message=message,
    )
    session.add(msg)
    ticket.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(msg)
    return msg


async def close_ticket(session: AsyncSession, ticket: SupportTicket) -> SupportTicket:
    ticket.status = SupportStatus.CLOSED.value
    ticket.closed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def get_open_tickets(session: AsyncSession) -> List[SupportTicket]:
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.status == SupportStatus.OPEN.value)
        .order_by(SupportTicket.created_at.asc())
    )
    return list(result.scalars().all())


async def get_ticket_by_id(session: AsyncSession, ticket_id: str) -> Optional[SupportTicket]:
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
    )
    return result.scalar_one_or_none()


async def get_customer_tickets(session: AsyncSession, customer_id: int) -> List[SupportTicket]:
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.customer_id == customer_id)
        .order_by(SupportTicket.created_at.desc())
    )
    return list(result.scalars().all())
