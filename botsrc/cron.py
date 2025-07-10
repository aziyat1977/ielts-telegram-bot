from aiocron import crontab
@crontab("0 12 * * *")  # UTC noon daily
async def remind():
    for uid, expires in due_in_days(3)+due_in_days(1):
        await bot.send_message(uid, "🔔 Your plan renews soon → tap 💳 Pay now")
