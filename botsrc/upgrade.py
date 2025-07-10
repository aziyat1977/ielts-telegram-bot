async def cmd_upgrade(msg):
    gallery = [
      ("🚀 VIP Coach • 449 900 so'm", "pay_vip"),
      ("✨ Pro Plus • 179 900 so'm",  "pay_pro"),
      ("🎓 Starter • 99 900 so'm",    "pay_start")
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(t, callback_data=d)] for t,d in gallery])
    await msg.answer("Choose plan:", reply_markup=kb)
@dp.callback_query(F.data.startswith("pay_"))
async def send_invoice(cb: CallbackQuery):
    plan = cb.data.split("_")[1]
    price = PLANS[plan]["price"]
    text = f"💳 Payme card 8600 1234 5678 ****\nSum: {price:,} so'm\nComment: RATER-{cb.from_user.id}"
    await cb.message.answer(text, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("✅ I’ve paid", callback_data=f'paid_{plan}')]]))
@dp.callback_query(F.data.startswith("paid_"))
async def ask_photo(cb):
    await cb.message.answer("📸 Send screenshot of Payme receipt")
    # next_message handling:
    s = await dp.wait_for(Message, F.photo, timeout=300)
    await bot.send_photo(ADMIN_CHANNEL_ID, s.photo[-1].file_id,
        caption=f"{cb.from_user.id}|{cb.data[5:]}")
    await cb.message.answer("⏳ Waiting for confirmation")
