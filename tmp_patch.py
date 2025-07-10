async def _reply_with_score(msg: Message, band: int, tips: list[str]) -> None:
    await msg.answer(f"🏅 <b>Band {band}</b>\n• " + "\n• ".join(tips))

    async with get_pool() as pool:
        credits = await pool.fetchval(
            "SELECT credits_left FROM users WHERE id=$1;",
            msg.from_user.id,
        )

    if credits is not None and credits <= 5:
        await msg.answer(
            f"⚠️ Only {credits} credit(s) left. Use /plans to top-up."
        )
