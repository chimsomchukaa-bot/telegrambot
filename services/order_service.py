from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Order, Customer, OrderStatus
from config.catalogue import VIP_CARDS, SERVICES
import pytz


async def generate_order_id(session: AsyncSession) -> str:
    year = datetime.now(pytz.timezone("America/New_York")).year
    prefix = f"CM-{year}-"
    result = await session.execute(
        select(func.count(Order.id)).where(Order.order_id.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    next_num = count + 1
    return f"{prefix}{next_num:04d}"


async def get_or_create_customer(
    session: AsyncSession,
    telegram_id: int,
    first_name: Optional[str] = None,
) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.telegram_id == telegram_id)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(telegram_id=telegram_id, first_name
