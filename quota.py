class QuotaMiddleware:
    async def __call__(self, handler, event, data):
        return await handler(event, data)

async def consume_credit_if_needed(*_a, **_kw):
    # Stars pay-wall removed – credits not needed
    return
