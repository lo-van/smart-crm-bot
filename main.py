import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, async_session
from handlers import routers
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils import get_forgotten_contacts
from models import User
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

async def check_forgotten_contacts(bot: Bot):
    """Фоновая задача: проверяет забытые контакты с учётом настроек пользователя."""
    async with async_session() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()
        now = datetime.now(timezone.utc)
        for user in users:
            # Проверяем, включены ли напоминания у пользователя
            if not user.reminders_enabled:
                continue

            # Проверяем, прошёл ли нужный интервал с последней проверки
            if user.last_remind_check_at is not None:
                next_check = user.last_remind_check_at + timedelta(days=user.remind_interval_days)
                # Если ещё не пора, пропускаем
                if now < next_check:
                    continue

            # Ищем забытые контакты
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

            # Обновляем время последней проверки
            user.last_remind_check_at = now
            await session.commit()

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    for router in routers:
        dp.include_router(router)

    # Планировщик: раз в час (просто проверяет условия)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_forgotten_contacts, 'interval', hours=1, args=(bot,))
    scheduler.start()

    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
