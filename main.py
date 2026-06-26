import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN
from database import init_db, async_session
from handlers import routers
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils import get_forgotten_contacts
from models import User
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

PROXY_URL = "socks5://127.0.0.1:1080"  # SOCKS-прокси AdGuard VPN

async def check_forgotten_contacts(bot: Bot):
    async with async_session() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()
        now = datetime.now(timezone.utc)
        for user in users:
            if not user.reminders_enabled:
                continue
            if user.last_remind_check_at is not None:
                next_check = user.last_remind_check_at + timedelta(days=user.remind_interval_days)
                if now < next_check:
                    continue
            contacts = await get_forgotten_contacts(user.id)
            if contacts:
                names = ", ".join(c.name for c in contacts[:5])
                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"🔔 Давно не общались: {names}. Может, написать?"
                    )
                except Exception as e:
                    print(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
            user.last_remind_check_at = now
            await session.commit()

async def main():
    await init_db()

    # Создаём сессию с прокси
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)

    dp = Dispatcher()
    for router in routers:
        dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_forgotten_contacts, 'interval', hours=1, args=(bot,))
    scheduler.start()

    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
