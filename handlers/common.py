from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import main_menu
from utils import (get_or_create_user, get_forgotten_contacts,
                   get_contact_by_id, set_remind_disabled, update_user_settings,
                   auto_tag_contact)
from icebreaker import generate_icebreaker
import asyncio
from userbot import run_sync_for_user
from datetime import datetime, timezone
from models import Contact
from database import async_session
from sqlalchemy import select

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "Привет! Я твоя умная CRM для контактов.\n"
        "/sync – синхронизировать контакты и чаты\n"
        "/remind – забытые контакты\n"
        "/remindset <дни> – установить интервал напоминаний (1-30)\n"
        "/remindset on|off – включить/отключить напоминания\n"
        "/autotag – автоматически проставить сферы и теги\n"
        "Используй меню 👇",
        reply_markup=main_menu
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start – главное меню\n"
        "/sync – синхронизировать контакты и чаты из Telegram\n"
        "/remind – показать, кому давно не писал\n"
        "/remindset – настройки напоминаний\n"
        "/autotag – автотегирование контактов\n"
        "/help – эта подсказка"
    )

@router.message(Command("sync"))
async def cmd_sync(message: Message, bot: Bot):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer("🔄 Запускаю синхронизацию...")
    asyncio.create_task(run_sync_for_user(message.from_user.id, bot=bot, chat_id=message.chat.id))

@router.message(Command("remind"))
@router.message(F.text == "⏰ Напоминания")
async def cmd_remind(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    contacts = await get_forgotten_contacts(user.id)
    if not contacts:
        await message.answer("Все контакты свежие, пока никому не нужно писать.")
        return
    text = "🔔 Давно не общались:\n\n"
    from keyboards import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for c in contacts[:15]:
        if c.last_contacted_at:
            last_dt = c.last_contacted_at
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_dt
            days = delta.days
            text += f"• {c.name} — {days} дн. назад\n"
        else:
            text += f"• {c.name} — никогда не общались\n"
        builder.button(text=f"💡 {c.name}", callback_data=f"ice_{c.id}")
        builder.button(text=f"🔇 {c.name}", callback_data=f"mute_{c.id}")
    builder.adjust(2)
    await message.answer(text, reply_markup=builder.as_markup())

@router.message(Command("remindset"))
async def cmd_remindset(message: Message):
    args = message.text.split()
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if len(args) < 2:
        await message.answer(
            f"Текущие настройки:\n"
            f"Интервал: {user.remind_interval_days} дн.\n"
            f"Напоминания: {'включены' if user.reminders_enabled else 'отключены'}\n\n"
            "Используйте:\n"
            "/remindset 7 – раз в 7 дней\n"
            "/remindset on – включить\n"
            "/remindset off – отключить"
        )
        return
    param = args[1].lower()
    if param in ("on", "off"):
        enabled = (param == "on")
        await update_user_settings(user.telegram_id, reminders_enabled=enabled)
        await message.answer(f"Напоминания {'включены' if enabled else 'отключены'}.")
    else:
        try:
            days = int(param)
            if days < 1 or days > 30:
                await message.answer("Интервал должен быть от 1 до 30 дней.")
                return
            await update_user_settings(user.telegram_id, remind_interval_days=days)
            await message.answer(f"Интервал напоминаний установлен: раз в {days} дн.")
        except ValueError:
            await message.answer("Неверный формат. Используйте число (1-30) или on/off.")

@router.message(Command("autotag"))
async def cmd_autotag(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    async with async_session() as session:
        contacts = (await session.execute(
            select(Contact).where(Contact.owner_id == user.id)
        )).scalars().all()
    if not contacts:
        await message.answer("Нет контактов для обработки.")
        return
    await message.answer(f"Запущено автотегирование для {len(contacts)} контактов...")
    for contact in contacts:
        await auto_tag_contact(contact.id)
    await message.answer("Автотегирование завершено.")

@router.callback_query(F.data.startswith("mute_"))
async def mute_contact(callback: CallbackQuery):
    contact_id = int(callback.data.split("_")[1])
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    contact = await get_contact_by_id(contact_id, user.id)
    if not contact:
        await callback.answer("Контакт не найден.", show_alert=True)
        return
    await set_remind_disabled(contact_id, True)
    await callback.answer(f"Контакт {contact.name} исключён из напоминаний.", show_alert=True)
    new_text = callback.message.text.replace(f"• {contact.name} — ", f"~~• {contact.name}~~ — ")
    await callback.message.edit_text(new_text, reply_markup=callback.message.reply_markup)

@router.callback_query(F.data.startswith("ice_"))
async def icebreaker_common(callback: CallbackQuery):
    contact_id = int(callback.data.split("_")[1])
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    contact = await get_contact_by_id(contact_id, user.id)
    if not contact:
        await callback.answer("Контакт не найден.", show_alert=True)
        return
    phrase = await generate_icebreaker(contact)
    await callback.message.answer(f"💬 Предлагаем начать диалог так:\n\n{phrase}")
    await callback.answer()
