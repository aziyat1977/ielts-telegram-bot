from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def passage_menu():
    rows = [
        [InlineKeyboardButton(text="📖 Show Passage", callback_data="show")],
        [
            InlineKeyboardButton(text="🇷🇺 RU", callback_data="tr_ru"),
            InlineKeyboardButton(text="🇺🇿 UZ", callback_data="tr_uz"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Prev", callback_data="prev"),
            InlineKeyboardButton(text="➡️ Next", callback_data="next"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
