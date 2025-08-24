import logging, asyncio
log = logging.getLogger("webhook")
async def handle_update(payload):
    # minimal default: just log and return
    log.info("update: keys=%s", list(payload.keys()))
