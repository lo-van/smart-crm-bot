from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить контакт")],
        [KeyboardButton(text="🔍 Найти контакт"), KeyboardButton(text="📋 Мои контакты")],
        [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="💡 Ледокол")]
    ],
    resize_keyboard=True
)

def skip_cancel_kb(with_skip: bool = True):
    builder = InlineKeyboardBuilder()
    if with_skip:
        builder.add(InlineKeyboardButton(text="Пропустить ➡️", callback_data="skip"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add"))
    return builder.as_markup()

def contacts_list_kb(contacts, page: int, total_pages: int):
    """Клавиатура для списка контактов – без кнопок удаления."""
    builder = InlineKeyboardBuilder()
    for c in contacts:
        builder.button(text=f"💡 {c.name}", callback_data=f"ice_{c.id}")
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons, width=2)
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_list"))
    return builder.as_markup()

def contact_card_kb(contact_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="💡 Ледокол", callback_data=f"ice_{contact_id}")
    builder.button(text="🔙 К списку", callback_data="back_to_list")
    return builder.as_markup()
