@dp.message(F.chat.id==ADMIN_CHANNEL_ID, F.text.startswith("/grant"))
async def grant(m: Message):
    uid, plan = m.text.split()[1:3]
    expires = datetime.utcnow()+timedelta(days=30)
    await db.execute("INSERT OR REPLACE INTO subs VALUES (?,?,?)", (uid, plan, expires))
    await bot.send_message(uid, "✅ Subscription activated!")
    await m.answer("Done")
