from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.data.reading_texts import PASSAGES
from app.bot.keyboards import passage_menu

router = Router()

# Fixed sample key for MVP
KEY = ("Cambridge 12","Test 5","Passage 1")

def joined(lines): return "\n\n".join(lines)

@router.message(F.text == "/start")
async def on_start(m: Message):
    title = PASSAGES[KEY]["title"]
    await m.answer(f"IELTS Reading • {title}\nChoose an action:", reply_markup=passage_menu())

@router.callback_query(F.data == "show")
async def on_show(c: CallbackQuery):
    en = PASSAGES[KEY]["english"]
    await c.message.edit_text("📖 *Passage (EN)*\n\n" + joined(en), parse_mode="Markdown")
    await c.message.edit_reply_markup(reply_markup=passage_menu())
    await c.answer()

@router.callback_query(F.data == "tr_ru")
async def on_ru(c: CallbackQuery):
    ru = PASSAGES[KEY]["ru"]
    await c.message.edit_text("🇷🇺 *Перевод (RU)*\n\n" + joined(ru), parse_mode="Markdown")
    await c.message.edit_reply_markup(reply_markup=passage_menu())
    await c.answer()

@router.callback_query(F.data == "tr_uz")
async def on_uz(c: CallbackQuery):
    uz = PASSAGES[KEY]["uz"]
    await c.message.edit_text("🇺🇿 *Tarjima (UZ)*\n\n" + joined(uz), parse_mode="Markdown")
    await c.message.edit_reply_markup(reply_markup=passage_menu())
    await c.answer()

@router.callback_query(F.data == "prev")
async def on_prev(c: CallbackQuery):
    await c.answer("Start of sample.", show_alert=False)

@router.callback_query(F.data == "next")
async def on_next(c: CallbackQuery):
    await c.answer("End of sample.", show_alert=False)
