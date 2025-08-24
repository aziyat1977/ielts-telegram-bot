from aiogram import Router, F, types
from .entitlements import grant, extend
from .metrics import bump
from .referrals import get_referrer, mark_rewarded_once

router = Router(name="payments")

TITLE="IELTS Pro — 30 days"
DESC ="Unlimited IELTS feedback (Writing + Speaking) for 30 days."
PRICES=[types.LabeledPrice(label="Pro 30d", amount=1490)]  # Stars; currency XTR

@router.message(F.text.in_({"/buy","Buy","buy"}))
async def buy(msg: types.Message):
    await msg.bot.send_invoice(
        chat_id=msg.chat.id,
        title=TITLE,
        description=DESC,
        payload="pro30",
        provider_token="",
        currency="XTR",
        prices=PRICES,
        start_parameter="pro30"
    )

@router.pre_checkout_query()
async def pcq(q: types.PreCheckoutQuery):
    await q.bot.answer_pre_checkout_query(pre_checkout_query_id=q.id, ok=True)

@router.message(F.successful_payment)
async def paid(msg: types.Message):
    ok = grant(msg.from_user.id, days=30)
    if ok:
        bump("pro_purchases")
        # Referral bonus: once per buyer (first ever purchase)
        try:
            rid = get_referrer(msg.from_user.id)
            if rid and rid != msg.from_user.id and mark_rewarded_once(msg.from_user.id):
                extend(rid, add_days=7)
                try:
                    await msg.bot.send_message(rid, "🎉 Your friend just bought Pro — you earned +7 days! Use /status to check.")
                except Exception:
                    pass
        except Exception:
            pass
        await msg.answer("✅ Payment received. Your *Pro* plan is active for 30 days. Use /status anytime.", parse_mode="Markdown")
    else:
        await msg.answer("✅ Payment received. ⚠️ Could not persist plan (temporary). We will enable your Pro shortly. Try /status again.")
