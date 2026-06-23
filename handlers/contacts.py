from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards import main_menu, skip_cancel_kb, contacts_list_kb
from utils import (add_contact, get_user_contacts, get_contact_by_id,
                   get_or_create_user, search_contacts)
from llm import extract_search_params
from icebreaker import generate_icebreaker
from datetime import datetime, timezone

router = Router()

class AddContact(StatesGroup):
    waiting_for_name = State()
    waiting_for_sphere = State()
    waiting_for_tags = State()
    waiting_for_notes = State()

# ... все хендлеры добавления контакта оставляем без изменений ...

# ---------- Просмотр контактов ----------
@router.message(F.text == "📋 Мои контакты")
async def list_contacts(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    contacts, total = await get_user_contacts(user.id, page=0)
    if not contacts:
        await message.answer("У вас пока нет контактов.")
        return
    text = "📇 Ваши контакты:\n"
    for i, c in enumerate(contacts, 1):
        text += f"{i}. {c.name} — {c.sphere or 'без сферы'}\n"
    total_pages = max(1, (total + 4) // 5)
    text += f"\nСтраница 1 из {total_pages}"
    await message.answer(text, reply_markup=contacts_list_kb(contacts, page=0, total_pages=total_pages))

@router.callback_query(F.data.startswith("page_"))
async def page_contacts(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    contacts, total = await get_user_contacts(user.id, page=page)
    total_pages = max(1, (total + 4) // 5)
    if not contacts:
        await callback.answer("Страница пуста.", show_alert=True)
        return
    text = "📇 Ваши контакты:\n"
    for i, c in enumerate(contacts, 1):
        text += f"{i}. {c.name} — {c.sphere or 'без сферы'}\n"
    text += f"\nСтраница {page+1} из {total_pages}"
    await callback.message.edit_text(text, reply_markup=contacts_list_kb(contacts, page, total_pages))
    await callback.answer()

@router.callback_query(F.data == "close_list")
async def close_list(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# ---------- Умный поиск ----------
@router.message(F.text, ~F.text.startswith("/"))
async def smart_search(message: Message):
    menu_buttons = ["➕ Добавить контакт", "🔍 Найти контакт", "📋 Мои контакты",
                    "⏰ Напоминания", "💡 Ледокол"]
    if message.text in menu_buttons:
        return
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer("🔍 Анализирую запрос и ищу подходящие контакты...")
    search_params = await extract_search_params(message.text)
    contacts = await search_contacts(search_params, user.id)
    if not contacts:
        await message.answer("Не найдено контактов по вашему запросу.")
        return
    text = f"🎯 Найдено контактов: {len(contacts)}\n\n"
    for i, c in enumerate(contacts, 1):
        last_seen = "никогда"
        if c.last_contacted_at:
            last_dt = c.last_contacted_at
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_dt
            days = delta.days
            last_seen = f"{days} дн. назад" if days > 0 else "сегодня"
        text += f"{i}. {c.name}\n   Сфера: {c.sphere or 'не указана'}\n   Общались: {last_seen}\n\n"
    from keyboards import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for c in contacts:
        builder.button(text=f"💡 {c.name}", callback_data=f"ice_{c.id}")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup())

# ---------- Ледокол ----------
@router.callback_query(F.data.startswith("ice_"))
async def icebreaker_callback(callback: CallbackQuery):
    contact_id = int(callback.data.split("_")[1])
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    contact = await get_contact_by_id(contact_id, user.id)
    if not contact:
        await callback.answer("Контакт не найден.", show_alert=True)
        return
    phrase = await generate_icebreaker(contact)
    await callback.message.answer(f"💬 Предлагаем начать диалог так:\n\n{phrase}")
    await callback.answer()

# ... заглушки для остальных кнопок ...
