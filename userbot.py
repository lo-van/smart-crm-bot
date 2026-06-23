import asyncio, traceback
from telethon import TelegramClient, functions
from userbot_config import API_ID, API_HASH, SESSION_NAME
from database import init_db, async_session
from models import User, Contact  # <-- явно импортируем Contact
from sqlalchemy import select
from datetime import datetime, timezone
from utils import upsert_contact_from_telegram, save_messages, update_last_contacted

MESSAGES_LIMIT = 200

async def sync_contacts_and_messages(bot_user_id: int, bot=None, chat_id=None):
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("Userbot авторизован")
    if bot:
        await bot.send_message(chat_id, "🔍 Userbot авторизован, начинаю синхронизацию...")

    try:
        result = await client(functions.contacts.GetContactsRequest(hash=0))
        users_list = result.users
        total = len(users_list)
        print(f"Найдено контактов: {total}")
        if bot:
            await bot.send_message(chat_id, f"📋 Найдено контактов: {total}")

        processed = 0
        for user in users_list:
            if user.bot:
                continue

            tg_user_id = user.id
            first_name = user.first_name or ''
            last_name = user.last_name or ''
            phone = getattr(user, 'phone', None)
            username = user.username

            processed += 1
            try:
                print(f"  [{processed}/{total}] Обрабатываю {first_name}...")
                db_contact = await upsert_contact_from_telegram(
                    user_id=bot_user_id,
                    tg_user_id=tg_user_id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    username=username
                )
                print(f"    Сохранён в БД (id={db_contact.id})")

                print(f"    Скачиваю сообщения...")
                messages = await client.get_messages(user, limit=MESSAGES_LIMIT)
                if messages:
                    msgs_data = []
                    last_date = None
                    for msg in messages:
                        if not msg.message and not msg.media:
                            continue
                        timestamp = msg.date.replace(tzinfo=timezone.utc)
                        if not last_date or timestamp > last_date:
                            last_date = timestamp
                        msgs_data.append({
                            "msg_id": msg.id,
                            "text": msg.message or "",
                            "timestamp": timestamp,
                            "from_me": msg.out,
                            "media_type": msg.media.__class__.__name__ if msg.media else None
                        })
                    await save_messages(db_contact.id, msgs_data)
                    if last_date:
                        await update_last_contacted(db_contact.id, last_date)
                    else:
                        await update_last_contacted(db_contact.id, None)
                    print(f"    Сохранено сообщений: {len(msgs_data)}")
                else:
                    print("    Нет сообщений")
                    await update_last_contacted(db_contact.id, None)
                    # Для контактов без истории – напомнить через 1 день
                    async with async_session() as session:
                        contact = await session.get(Contact, db_contact.id)
                        if contact:
                            contact.remind_interval_days = 1
                            await session.commit()
            except Exception as e:
                err = f"❌ Ошибка на {first_name}: {str(e)[:200]}"
                print(err)
                traceback.print_exc()
                if bot:
                    await bot.send_message(chat_id, err)

        if bot:
            await bot.send_message(chat_id, f"✅ Обработано {processed} контактов. Проверьте «Мои контакты».")
    except Exception as e:
        err = f"❌ Глобальная ошибка: {str(e)[:200]}"
        print(err)
        traceback.print_exc()
        if bot:
            await bot.send_message(chat_id, err)
    finally:
        await client.disconnect()

async def run_sync_for_user(telegram_id: int, bot=None, chat_id=None):
    await init_db()
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            if bot:
                await bot.send_message(chat_id, "❌ Пользователь не найден. Сначала /start")
            return
        await sync_contacts_and_messages(user.id, bot=bot, chat_id=chat_id)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tg_id = int(sys.argv[1])
    else:
        tg_id = int(input("Введите ваш Telegram ID: "))
    asyncio.run(run_sync_for_user(tg_id))
