# plans.py — credit packs & model routing
#
# Star prices give ≈ 70 % net margin after Telegram’s 3 % fee.
# One “credit” = 1 essay OR 1 speaking score (~1 k tokens total).

PLANS: dict[str, dict[str, int | str]] = {
    # plan-id : {OpenAI model, Stars price, #credits}
    "starter": {
        "model":   "gpt-3.5-turbo",   # solid, budget-friendly
        "stars":    25,               # 25 ⭐ ≈ $0.25
        "credits":  60,
    },
    "advance": {                      # better quality, still cheap
        "model":   "gpt-4o-mini",
        "stars":    90,               # 90 ⭐ ≈ $0.90
        "credits": 150,
    },
    "pro": {                          # high-fidelity feedback
        "model":   "gpt-4o",
        "stars":   700,               # 700 ⭐ ≈ $7.00
        "credits": 200,
    },
    "ultra": {                        # ultra-detailed (128 k ctx)
        "model":   "gpt-4o-128k",     # swap for 4-turbo/4-1 when GA
        "stars":  1200,               # 1 200 ⭐ ≈ $12.00
        "credits": 200,
    },
}
