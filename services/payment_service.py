from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Payment, Order, PaymentStatus, OrderStatus


async def create_payment_submission(
    session: AsyncSession,
    order: Order,
    screenshot_file_id: str,
    extracted_info: str = "",
) -> Payment:
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.PENDING_VERIFICATION.value,
        screenshot_file_id=screenshot_file_id,
        extracted_info=extracted_info or "Screenshot submitted – pending manual review.",
    )
    session.add(payment)
    order.status = OrderStatus.PENDING_VERIFICATION.value
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_pending_payments(session: AsyncSession) -> list[Payment]:
    result = await session.execute(
        select(Payment)
        .where(Payment.status == PaymentStatus.PENDING_VERIFICATION.value)
        .order_by(Payment.created_at.asc())
    )
    return list(result.scalars().all())


async def update_payment_status(
    session: AsyncSession,
    payment_id: int,
    new_status: str,
    admin_note: str = "",
) -> Optional[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return None

    payment.status = new_status
    if admin_note:
        payment.admin_note = admin_note

    order_result = await session.execute(
        select(Order).where(Order.id == payment.order_id)
    )
    order = order_result.scalar_one()
    order.status = new_status

    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_by_id(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()
