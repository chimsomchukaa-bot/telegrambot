from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "Pending Payment"
    PENDING_VERIFICATION = "Pending Verification"
    VERIFIED = "Verified"
    REJECTED = "Rejected"
    NEEDS_MORE_INFO = "Needs More Info"
    CANCELLED = "Cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING_VERIFICATION = "Pending Verification"
    VERIFIED = "Verified"
    REJECTED = "Rejected"
    NEEDS_MORE_INFO = "Needs More Info"


class SupportStatus(str, enum.Enum):
    OPEN = "Open"
    CLOSED = "Closed"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="customer"
    )
    conversation_messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="customer"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    item_type: Mapped[str] = mapped_column(String(50))
    item_key: Mapped[str] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default=OrderStatus.PENDING_PAYMENT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[str] = mapped_column(String(50), default=PaymentStatus.PENDING_VERIFICATION.value)
    screenshot_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extracted_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped["Order"] = relationship("Order", back_populates="payments")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    category: Mapped[str] = mapped_column(String(50))
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=SupportStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="support_tickets")
    messages: Mapped[List["SupportMessage"]] = relationship(
        "SupportMessage", back_populates="ticket"
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"))
    sender_type: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship("Customer", back_populates="conversation_messages")
