import random
from models import Contact
from database import async_session
from sqlalchemy import select, func
from datetime import datetime, timezone

# Заготовки фраз
ICE_TEMPLATES = [
    "Привет, {name}! Давно не виделись. Как продвигаются дела в сфере {sphere}?",
    "Здравствуй, {name}! Вспомнил о тебе, расскажи, что нового в {sphere}.",
    "{name}, привет! Как жизнь? Чем сейчас занимаешься в области {sphere}?",
    "Привет, {name}! Решил узнать, как у тебя дела. {sphere_note}",
    "Здравствуй, {name}! Давно не общались, очень интересно, что у тебя происходит в {sphere}.",
    "Слушай, {name}, есть минутка? Хотел спросить про {sphere} – может, есть что-то новое?"
]

async def get_recent_messages(contact_id: int, limit: int = 3):
    """Получить последние сообщения с контактом."""
    async with async_session() as session:
        from models import Message
        result = await session.execute(
            select(Message)
            .where(Message.contact_id == contact_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

async def generate_icebreaker(contact: Contact) -> str:
    """Создать ледокол на основе данных контакта."""
    name = contact.name.split()[0] if contact.name else "друг"
    sphere = contact.sphere or "твоей деятельности"
    sphere_note = ""
    if contact.sphere:
        sphere_note = f"(сфера: {contact.sphere})"
    
    # Пытаемся извлечь тему из последних сообщений
    topic = None
    messages = await get_recent_messages(contact.id)
    if messages:
        # Простейший анализ: ищем слово "проект", "работа", "встреча" и т.п.
        keywords = ["проект", "работа", "встреча", "запуск", "новость", "план", "идея", "лендинг", "дизайн"]
        for msg in messages:
            if msg.text:
                text_lower = msg.text.lower()
                for kw in keywords:
                    if kw in text_lower:
                        topic = kw
                        break
            if topic:
                break
    
    # Формируем базовую фразу
    template = random.choice(ICE_TEMPLATES)
    phrase = template.format(name=name, sphere=sphere, sphere_note=sphere_note)
    
    # Если нашли тему, добавляем уточнение
    if topic:
        topic_phrase = f" Помнишь, мы обсуждали {topic}? Как там успехи?"
        phrase += topic_phrase
    
    return phrase
