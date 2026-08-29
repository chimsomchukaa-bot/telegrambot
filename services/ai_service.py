from typing import List, Dict, Optional
import google.generativeai as genai
from config.settings import settings
from prompts.system_prompt import SYSTEM_PROMPT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import ConversationMessage, Customer
import asyncio

genai.configure(api_key=settings.gemini_api_key)

model = genai.GenerativeModel(
    model_name=settings.gemini_model,
    system_instruction=SYSTEM_PROMPT,
    generation_config={
        "temperature": 0.3,
        "max_output_tokens": 1200,
        "top_p": 0.95,
    },
)


async def get_conversation_history(
    session: AsyncSession, customer_id: int, limit: int = 20
) -> List[Dict[str, str]]:
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.customer_id == customer_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def save_message(
    session: AsyncSession, customer_id: int, role: str, content: str
):
    msg = ConversationMessage(customer_id=customer_id, role=role, content=content)
    session.add(msg)
    await session.commit()


def _build_gemini_history(history: List[Dict[str, str]]) -> list:
    gemini_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    return gemini_history


async def generate_ai_response(
    session: AsyncSession,
    customer: Customer,
    user_message: str,
    extra_context: Optional[str] = None,
) -> str:
    history = await get_conversation_history(session, customer.id)

    context_parts = []
    if customer.first_name:
        context_parts.append(f"Customer's first name: {customer.first_name}")
    if customer.full_name:
        context_parts.append(f"Full name: {customer.full_name}")
    if customer.email:
        context_parts.append(f"Email: {customer.email}")
    if customer.country:
        context_parts.append(f"Country: {customer.country}")
    if extra_context:
        context_parts.append(extra_context)

    final_user_message = user_message
    if context_parts:
        context_block = "Known customer information:\n" + "\n".join(context_parts)
        final_user_message = f"{context_block}\n\nCustomer message: {user_message}"

    try:
        def _call_gemini():
            chat = model.start_chat(history=_build_gemini_history(history))
            response = chat.send_message(final_user_message)
            return response.text.strip()

        reply = await asyncio.to_thread(_call_gemini)
    except Exception as e:
        reply = (
            "I apologise, but I am experiencing a temporary technical issue. "
            "Please try again in a moment or contact support if the problem persists.\n\n"
            "Celebrity Management Team"
        )
        print(f"Gemini AI Error: {e}")

    await save_message(session, customer.id, "user", user_message)
    await save_message(session, customer.id, "assistant", reply)
    return reply
