from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session
from models import User, Contact, Message
from datetime import datetime, timezone

async def get_or_create_user(tg_id: int, username: str | None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=tg_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

async def add_contact(user_id: int, name: str, sphere: str | None,
                     tags: str | None, notes: str | None) -> Contact:
    async with async_session() as session:
        contact = Contact(owner_id=user_id, name=name, sphere=sphere, tags=tags, notes=notes)
        session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact

async def get_user_contacts(user_id: int, page: int = 0, per_page: int = 5):
    async with async_session() as session:
        offset = page * per_page
        cnt = await session.scalar(select(func.count(Contact.id)).where(Contact.owner_id == user_id))
        result = await session.execute(
            select(Contact).where(Contact.owner_id == user_id)
            .order_by(Contact.created_at.desc()).offset(offset).limit(per_page)
        )
        return result.scalars().all(), cnt

async def get_contact_by_id(contact_id: int, user_id: int) -> Contact | None:
    async with async_session() as session:
        result = await session.execute(
            select(Contact).where(Contact.id == contact_id, Contact.owner_id == user_id)
        )
        return result.scalar_one_or_none()

async def upsert_contact_from_telegram(user_id: int, tg_user_id: int,
                                       first_name: str, last_name: str | None,
                                       phone: str | None, username: str | None) -> Contact:
    async with async_session() as session:
        result = await session.execute(
            select(Contact).where(and_(Contact.owner_id == user_id, Contact.telegram_user_id == tg_user_id))
        )
        contact = result.scalar_one_or_none()
        name = f"{first_name} {last_name or ''}".strip()
        if contact:
            contact.name = name
            contact.phone = phone
            contact.telegram_handle = username
            contact.last_synced_at = datetime.now(timezone.utc)
        else:
            contact = Contact(owner_id=user_id, telegram_user_id=tg_user_id, name=name,
                              phone=phone, telegram_handle=username,
                              last_synced_at=datetime.now(timezone.utc), remind_interval_days=1)
            session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact

async def save_messages(contact_id: int, messages_data: list):
    async with async_session() as session:
        for msg in messages_data:
            existing = await session.scalar(
                select(Message).where(and_(Message.contact_id == contact_id, Message.telegram_message_id == msg["msg_id"]))
            )
            if not existing:
                session.add(Message(contact_id=contact_id, telegram_message_id=msg["msg_id"],
                                    text=msg.get("text", ""), timestamp=msg["timestamp"],
                                    from_me=msg.get("from_me", False), media_type=msg.get("media_type")))
        await session.commit()

async def update_last_contacted(contact_id: int, last_date: datetime | None):
    async with async_session() as session:
        result = await session.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if contact:
            contact.last_contacted_at = last_date
            await session.commit()

async def search_contacts(query_params: dict, user_id: int, limit: int = 10) -> list[Contact]:
    keywords = query_params.get("keywords", [])
    sphere = query_params.get("sphere")
    async with async_session() as session:
        base_filter = [Contact.owner_id == user_id]
        text_filters = []
        if sphere:
            text_filters.append(Contact.sphere.ilike(f"%{sphere}%"))
        for kw in keywords:
            like_pattern = f"%{kw}%"
            text_filters.append(or_(Contact.name.ilike(like_pattern), Contact.sphere.ilike(like_pattern),
                                    Contact.tags.ilike(like_pattern), Contact.notes.ilike(like_pattern)))
        if text_filters:
            base_filter.append(or_(*text_filters))
        stmt = select(Contact).where(and_(*base_filter)).limit(limit * 2)
        result = await session.execute(stmt)
        contacts = result.scalars().all()
        if len(contacts) < limit and keywords:
            msg_filter = [Message.text.ilike(f"%{kw}%") for kw in keywords]
            msg_stmt = select(Contact.id).join(Message, Message.contact_id == Contact.id).where(
                and_(Contact.owner_id == user_id, or_(*msg_filter))).distinct()
            msg_result = await session.execute(msg_stmt)
            contact_ids_from_messages = [row[0] for row in msg_result]
            existing_ids = {c.id for c in contacts}
            new_ids = [cid for cid in contact_ids_from_messages if cid not in existing_ids]
            if new_ids:
                extra_stmt = select(Contact).where(Contact.id.in_(new_ids)).limit(limit)
                extra_result = await session.execute(extra_stmt)
                contacts.extend(extra_result.scalars().all())
        contacts.sort(key=lambda c: c.last_contacted_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return contacts[:limit]

async def get_forgotten_contacts(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Contact).where(
                and_(
                    Contact.owner_id == user_id,
                    Contact.remind_disabled == False,
                    or_(
                        Contact.last_contacted_at.is_(None),
                        Contact.last_contacted_at < func.datetime('now', '-90 days')
                    )
                )
            )
        )
        return result.scalars().all()

async def set_remind_disabled(contact_id: int, disabled: bool = True):
    async with async_session() as session:
        result = await session.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if contact:
            contact.remind_disabled = disabled
            await session.commit()
            return True
        return False

async def update_user_settings(telegram_id: int, remind_interval_days: int = None,
                               reminders_enabled: bool = None):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if remind_interval_days is not None:
            user.remind_interval_days = remind_interval_days
        if reminders_enabled is not None:
            user.reminders_enabled = reminders_enabled
        await session.commit()
        return user

from tag_rules import RULES

async def auto_tag_contact(contact_id: int):
    """Автоматически проставляет сферу и теги контакту на основе его сообщений."""
    async with async_session() as session:
        contact = await session.get(Contact, contact_id)
        if not contact:
            return
        # Получаем текст последних 200 сообщений
        messages = (await session.execute(
            select(Message).where(Message.contact_id == contact_id).order_by(Message.timestamp.desc()).limit(200)
        )).scalars().all()
        text = " ".join([m.text or "" for m in messages]).lower()
        if not text:
            return
        # Подсчитываем вхождения ключевых слов по каждой категории
        scores = {}
        for category, rule in RULES.items():
            score = 0
            for kw in rule["keywords"]:
                score += text.count(kw.lower())
            if score > 0:
                scores[category] = score
        if not scores:
            return
        # Выбираем категорию с максимальным счётом
        best_category = max(scores, key=scores.get)
        rule = RULES[best_category]
        contact.sphere = rule["sphere"]
        contact.tags = ", ".join(rule["tags"])
        await session.commit()
