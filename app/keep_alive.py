"""
Keep-Alive module for Render Free Tier.
Runs a lightweight HTTP server + self-ping loop to prevent the service from sleeping.
"""

import asyncio
import os
import logging
from aiohttp import web, ClientSession

logger = logging.getLogger(__name__)

# Render assigns PORT env var for web services
PORT = int(os.environ.get("PORT", 10000))

# Self-ping interval (seconds) — Render sleeps after 15 min, so ping every 10 min
PING_INTERVAL = 600  # 10 minutes

# Your Render service URL (set as env var on Render dashboard)
# Example: https://your-bot-name.onrender.com
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")


async def health_handler(request):
    """Health check endpoint — returns 200 OK."""
    return web.Response(text="✅ Bot is alive!", status=200)


async def home_handler(request):
    """Root endpoint with basic info."""
    return web.Response(
        text="🤖 Locket Gold Bot is running!",
        content_type="text/plain",
        status=200,
    )


async def self_ping_loop():
    """
    Periodically pings own URL to prevent Render free tier from sleeping.
    Falls back gracefully if RENDER_EXTERNAL_URL is not set.
    """
    if not RENDER_EXTERNAL_URL:
        logger.warning(
            "⚠️ RENDER_EXTERNAL_URL not set — self-ping disabled. "
            "Set it in Render Environment Variables to keep the bot awake."
        )
        return

    ping_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/health"
    logger.info(f"🏓 Self-ping enabled: {ping_url} every {PING_INTERVAL}s")

    await asyncio.sleep(30)  # Wait for server to fully start

    async with ClientSession() as session:
        while True:
            try:
                async with session.get(ping_url, timeout=15) as resp:
                    logger.info(f"🏓 Self-ping OK — Status: {resp.status}")
            except Exception as e:
                logger.warning(f"🏓 Self-ping failed: {e}")

            await asyncio.sleep(PING_INTERVAL)


async def start_keep_alive():
    """
    Starts the HTTP server and self-ping loop.
    Call this from your bot's post_init hook.
    """
    # --- HTTP Server ---
    app = web.Application()
    app.router.add_get("/", home_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌐 Keep-alive HTTP server started on port {PORT}")

    # --- Self-Ping Loop ---
    asyncio.create_task(self_ping_loop())
