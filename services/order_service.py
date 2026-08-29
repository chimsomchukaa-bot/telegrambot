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
        customer = Customer(telegram_id=telegram_id, first_name=first_name)
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
    elif first_name and not customer.first_name:
        customer.first_name = first_name
        await session.commit()
    return customer


async def update_customer_details(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    email: str,
    country: str,
) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.telegram_id == telegram_id)
    )
    customer = result.scalar_one()
    customer.full_name = full_name
    customer.email = email
    customer.country = country
    if full_name:
        customer.first_name = full_name.strip().split()[0]
    await session.commit()
    await session.refresh(customer)
    return customer


async def has_open_order(session: AsyncSession, customer_id: int) -> bool:
    open_statuses = [
        OrderStatus.PENDING_PAYMENT.value,
        OrderStatus.PENDING_VERIFICATION.value,
        OrderStatus.NEEDS_MORE_INFO.value,
    ]
    result = await session.execute(
        select(Order).where(
            and_(
                Order.customer_id == customer_id,
                Order.status.in_(open_statuses),
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def create_order(
    session: AsyncSession,
    customer: Customer,
    item_type: str,
    item_key: str,
) -> Tuple[Order, str]:
    if await has_open_order(session, customer.id):
        return None, "You already have an open order. Please complete or cancel it before placing a new one."

    if item_type == "vip_card":
        item = VIP_CARDS.get(item_key)
        if not item:
            return None, "Invalid VIP card selected."
    elif item_type == "service":
        item = SERVICES.get(item_key)
        if not item:
            return None, "Invalid service selected."
    else:
        return None, "Invalid item type."

    order_id = await generate_order_id(session)
    order = Order(
        order_id=order_id,
        customer_id=customer.id,
        item_type=item_type,
        item_key=item_key,
        item_name=item["name"],
        price=item["price"],
        currency=item.get("currency", "USD"),
        status=OrderStatus.PENDING_PAYMENT.value,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order, ""


async def get_customer_orders(session: AsyncSession, customer_id: int) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


async def get_order_by_order_id(session: AsyncSession, order_id: str) -> Optional[Order]:
    result = await session.execute(
        select(Order).where(Order.order_id == order_id)
    )
    return result.scalar_one_or_none()


async def update_order_status(
    session: AsyncSession, order_id: str, new_status: str
) -> Optional[Order]:
    order = await get_order_by_order_id(session, order_id)
    if order:
        order.status = new_status
        await session.commit()
        await session.refresh(order)
    return order
